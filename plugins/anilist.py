"""
AniList adapter — public GraphQL API, no API key required.
https://anilist.gitbook.io/anilist-apiv2-docs/
"""

import time

import requests

from config import ANILIST_ENDPOINT, CATALOG_CACHE_TTL
from plugins.base import AnimeSource



SEARCH_QUERY = """
query ($search: String, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo { hasNextPage }
    media(search: $search, type: ANIME, isAdult: true, sort: SEARCH_MATCH) {
      id
      title { romaji english native }
      startDate { year }
      coverImage { extraLarge large }
      averageScore
      genres
      format
      episodes
      isAdult
    }
  }
}
"""

# Broader anime search (no isAdult filter) — used as a fallback so titles
# mis-tagged on AniList still surface; we keep only adult / Hentai hits.
SEARCH_ANIME_BROAD_QUERY = """
query ($search: String, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo { hasNextPage }
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      id
      title { romaji english native }
      startDate { year }
      coverImage { extraLarge large }
      averageScore
      genres
      format
      episodes
      isAdult
    }
  }
}
"""

DETAILS_QUERY = """
query ($id: Int) {
  Media(id: $id) {
    id
    type
    title { romaji english }
    startDate { year month day }
    coverImage { large extraLarge }
    bannerImage
    description(asHtml: false)
    genres
    averageScore
    status
    episodes
    chapters
    format
    duration
    countryOfOrigin
    relations {
      edges {
        relationType
        node { id type title { romaji english } coverImage { large } }
      }
    }
  }
}
"""

# Adult discovery — used by Trending / Top Airing / Popular
# BL / gay / boys love filtered out after fetch (uses full genres + tags)
DISCOVER_QUERY = """
query ($sort: [MediaSort], $page: Int) {
  Page(page: $page, perPage: 10) {
    pageInfo { hasNextPage }
    media(type: ANIME, isAdult: true, sort: $sort) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      genres
      tags { name }
      episodes
      description(asHtml: false)
    }
  }
}
"""

DISCOVER_AIRING_QUERY = """
query ($sort: [MediaSort], $page: Int) {
  Page(page: $page, perPage: 10) {
    pageInfo { hasNextPage }
    media(type: ANIME, isAdult: true, sort: $sort, status: RELEASING) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      genres
      tags { name }
      episodes
      description(asHtml: false)
    }
  }
}
"""

GENRE_QUERY = """
query ($genre: String, $page: Int, $type: MediaType) {
  Page(page: $page, perPage: 36) {
    pageInfo { hasNextPage }
    media(type: $type, isAdult: true, genre: $genre, sort: POPULARITY_DESC) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      type
    }
  }
}
"""

# Adult manga / manhwa / doujinshi (pornhwa). Labels in the UI stay
# "Manga / Manhwa" — content includes ONE_SHOT (doujin) + KR manhwa + manga.
MANGA_DISCOVER_QUERY = """
query ($sort: [MediaSort], $page: Int) {
  Page(page: $page, perPage: 36) {
    pageInfo { hasNextPage }
    media(
      type: MANGA
      isAdult: true
      format_in: [MANGA, ONE_SHOT, NOVEL]
      genre_not_in: ["Yaoi"]
      sort: $sort
    ) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      genres
      tags { name }
      chapters
      format
      countryOfOrigin
      description(asHtml: false)
    }
  }
}
"""

MANHWA_DISCOVER_QUERY = """
query ($sort: [MediaSort], $page: Int) {
  Page(page: $page, perPage: 36) {
    pageInfo { hasNextPage }
    media(
      type: MANGA
      isAdult: true
      countryOfOrigin: KR
      format_in: [MANGA, ONE_SHOT]
      genre_not_in: ["Yaoi"]
      sort: $sort
    ) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      genres
      tags { name }
      chapters
      format
      countryOfOrigin
      description(asHtml: false)
    }
  }
}
"""

# Ongoing adult manga / manhwa / doujin (status RELEASING)
MANGA_AIRING_QUERY = """
query ($sort: [MediaSort], $page: Int) {
  Page(page: $page, perPage: 36) {
    pageInfo { hasNextPage }
    media(
      type: MANGA
      isAdult: true
      status: RELEASING
      format_in: [MANGA, ONE_SHOT, NOVEL]
      genre_not_in: ["Yaoi"]
      sort: $sort
    ) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      genres
      tags { name }
      chapters
      format
      countryOfOrigin
      description(asHtml: false)
    }
  }
}
"""

MANGA_SEARCH_QUERY = """
query ($search: String, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo { hasNextPage }
    media(
      search: $search
      type: MANGA
      isAdult: true
      sort: SEARCH_MATCH
    ) {
      id
      title { romaji english native }
      startDate { year }
      coverImage { extraLarge large }
      averageScore
      genres
      format
      chapters
      countryOfOrigin
      isAdult
    }
  }
}
"""

# Broader manga/manhwa/manhua/novel search without isAdult — filter after.
SEARCH_MANGA_BROAD_QUERY = """
query ($search: String, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo { hasNextPage }
    media(
      search: $search
      type: MANGA
      sort: SEARCH_MATCH
    ) {
      id
      title { romaji english native }
      startDate { year }
      coverImage { extraLarge large }
      averageScore
      genres
      format
      chapters
      countryOfOrigin
      isAdult
    }
  }
}
"""

# Explicit BL / Yaoi adult manga+manhwa — general adult feeds are dominated by
# hetero hentai, so Yaoi titles rarely surface in the top page without a
# dedicated query. Genre "Yaoi" is AniList's adult BL label.
BL_DISCOVER_QUERY = """
query ($sort: [MediaSort], $page: Int) {
  Page(page: $page, perPage: 36) {
    pageInfo { hasNextPage }
    media(
      type: MANGA
      isAdult: true
      genre: "Yaoi"
      format_in: [MANGA, ONE_SHOT, NOVEL]
      sort: $sort
    ) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      genres
      chapters
      format
      countryOfOrigin
      description(asHtml: false)
    }
  }
}
"""

BL_AIRING_QUERY = """
query ($sort: [MediaSort], $page: Int) {
  Page(page: $page, perPage: 36) {
    pageInfo { hasNextPage }
    media(
      type: MANGA
      isAdult: true
      genre: "Yaoi"
      status: RELEASING
      format_in: [MANGA, ONE_SHOT, NOVEL]
      sort: $sort
    ) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      genres
      chapters
      format
      countryOfOrigin
      description(asHtml: false)
    }
  }
}
"""

BL_MANHWA_QUERY = """
query ($sort: [MediaSort], $page: Int) {
  Page(page: $page, perPage: 36) {
    pageInfo { hasNextPage }
    media(
      type: MANGA
      isAdult: true
      genre: "Yaoi"
      countryOfOrigin: KR
      format_in: [MANGA, ONE_SHOT]
      sort: $sort
    ) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      genres
      chapters
      format
      countryOfOrigin
      description(asHtml: false)
    }
  }
}
"""


def _clean_description(html: str | None) -> str:
    if not html:
        return ""
    text = html.replace("<br>", "\n").replace("<br/>", "\n").replace("<i>", "").replace("</i>", "")
    return text.strip()


def _best_title(title_obj: dict) -> str:
    return title_obj.get("english") or title_obj.get("romaji") or "Untitled"


# Genres / tags that should never appear in Trending / Top Airing / Popular
# Only gay / BL / boys love — adult hentai and regular (hetero) manhwa stay
_BLOCKED_GENRES = {
    "yaoi", "boys love", "boys' love", "boy's love",
    "bl", "gay", "shounen ai", "bara",
}

_BLOCKED_TAGS = {
    "yaoi", "boys' love", "boys love", "boy's love",
    "shounen ai", "bara", "gay", "male on male",
    "mlm", "bl",
}

_BLOCKED_TITLE_KW = (
    "yaoi", "boys love", "boy's love", "boys' love",
    " (bl)", "[bl]", " bl ", "-bl ", " bl-",
)


def _is_blocked_item(item: dict) -> bool:
    """Return True if the item should be hidden (gay / BL / boys love)."""
    # Full genre list (not the truncated display list)
    for g in item.get("genres") or []:
        if g and str(g).strip().lower() in _BLOCKED_GENRES:
            return True
    # AniList tags (stronger signal for KR BL manhwa)
    for t in item.get("tags") or []:
        name = t if isinstance(t, str) else (t.get("name") if isinstance(t, dict) else None)
        if name and str(name).strip().lower() in _BLOCKED_TAGS:
            return True
    # Title safety net
    title = (item.get("title") or "").lower()
    if any(kw in title for kw in _BLOCKED_TITLE_KW):
        return True
    return False


def _filter_blocked(results: list) -> list:
    """Drop gay / BL / Yaoi / boys love items from a results list."""
    return [r for r in results if not _is_blocked_item(r)]


class AniListSource(AnimeSource):
    name = "anilist"

    def __init__(self):
        self._cache: dict[str, tuple[float, dict]] = {}
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "HIndexBot/1.0 (catalog)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _post(self, query: str, variables: dict) -> dict:
        # AniList rate-limits aggressively. Retry 429s; also tolerate
        # GraphQL error payloads so one bad variable never 500s the app.
        last_exc = None
        for attempt in range(3):
            try:
                resp = self._session.post(
                    ANILIST_ENDPOINT,
                    json={"query": query, "variables": variables},
                    timeout=15,
                )
            except requests.RequestException as e:
                last_exc = e
                time.sleep(0.5 * (attempt + 1))
                continue
            if resp.status_code == 429:
                last_exc = requests.HTTPError(
                    f"429 rate limited (attempt {attempt + 1})", response=resp
                )
                retry_after = resp.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.8 * (attempt + 1)
                time.sleep(delay)
                continue
            if resp.status_code >= 400:
                last_exc = requests.HTTPError(
                    f"AniList HTTP {resp.status_code}", response=resp
                )
                time.sleep(0.4 * (attempt + 1))
                continue
            try:
                body = resp.json()
            except ValueError as e:
                last_exc = e
                continue
            if body.get("errors") and not body.get("data"):
                last_exc = requests.HTTPError(
                    f"AniList GraphQL error: {body['errors'][0].get('message', 'unknown')}"
                )
                break
            data = body.get("data")
            if data is None:
                last_exc = requests.HTTPError("AniList returned empty data")
                break
            return data
        raise last_exc if last_exc else requests.HTTPError("AniList request failed")

    def _map_search_item(self, m: dict, media_type: str) -> dict:
        score = m.get("averageScore")
        item = {
            "source": self.name,
            "source_id": m["id"],
            "anilist_id": m["id"],
            "title": _best_title(m.get("title") or {}),
            "year": (m.get("startDate") or {}).get("year"),
            "poster_url": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large"),
            "rating": round(score / 10, 1) if score else None,
            "genres": (m.get("genres") or [])[:3],
            "format": m.get("format"),
            "media_type": media_type,
            "isAdult": bool(m.get("isAdult")),
        }
        if media_type == "ANIME":
            item["episodes"] = m.get("episodes")
        else:
            item["chapters"] = m.get("chapters")
            item["countryOfOrigin"] = m.get("countryOfOrigin")
        return item

    @staticmethod
    def _is_adult_result(m: dict) -> bool:
        if m.get("isAdult"):
            return True
        genres = {str(g).strip().lower() for g in (m.get("genres") or [])}
        # Include common adult-adjacent genres so mis-tagged pornhwa / hentai
        # (and novels) still appear in search.
        return bool(genres & {"hentai", "yaoi", "yuri", "ecchi"})

    def search(self, query: str, page: int = 1) -> dict:
        """Search ALL anime on AniList (no isAdult filter).

        Returns every matching anime title so search surfaces hentai,
        regular anime, and everything else.
        """
        results = []
        seen = set()
        has_next = False
        try:
            data = self._post(SEARCH_ANIME_BROAD_QUERY, {"search": query, "page": page})
            for m in data["Page"]["media"]:
                mid = m["id"]
                if mid in seen:
                    continue
                seen.add(mid)
                results.append(self._map_search_item(m, "ANIME"))
            has_next = data["Page"]["pageInfo"]["hasNextPage"]
        except Exception:
            pass
        return {"results": results, "has_next": has_next}

    def search_all(self, query: str, page: int = 1) -> dict:
        """Search ALL AniList anime + manga/manhwa/manhua/novels together.

        No adult-only filter — every matching title is returned so the
        search page shows pornhwa, hentai, novels, manhua, manhwa, and
        regular titles in one list.
        """
        anime = {"results": [], "has_next": False}
        manga = {"results": [], "has_next": False}
        try:
            anime = self.search(query, page)
        except Exception:
            pass
        try:
            manga = self.search_manga(query, page)
        except Exception:
            pass
        seen = set()
        merged = []
        for item in (anime.get("results") or []) + (manga.get("results") or []):
            aid = item.get("anilist_id") or item.get("source_id")
            if aid in seen:
                continue
            seen.add(aid)
            merged.append(item)
        return {
            "results": merged,
            "has_next": bool(anime.get("has_next") or manga.get("has_next")),
        }

    def get_details(self, source_id, use_cache: bool = True) -> dict:
        if use_cache:
            return self._cached(
                f"details:{source_id}",
                lambda: self._fetch_details(source_id),
                ttl=CATALOG_CACHE_TTL,
            )
        return self._fetch_details(source_id)

    def _fetch_details(self, source_id) -> dict:
        data = self._post(DETAILS_QUERY, {"id": int(source_id)})
        m = data["Media"]
        score = m.get("averageScore")
        titles = m.get("title") or {}
        main_title = _best_title(titles)
        alt_title = titles.get("romaji") if titles.get("english") else None
        if alt_title == main_title:
            alt_title = None

        # Every relation type that's still genuinely "this anime" (another
        # season, an OVA/movie tied to the story, a spin-off, an alternate
        # cut/compilation) — not just direct prequel/sequel — so a join
        # link set anywhere propagates across the whole franchise. Left out
        # on purpose: ADAPTATION (source manga/novel), CHARACTER (unrelated
        # series that merely shares a guest character), and OTHER (too
        # loose — often crossovers with no real franchise connection).
        SAME_FRANCHISE_RELATIONS = {
            "PREQUEL", "SEQUEL", "SIDE_STORY", "PARENT",
            "ALTERNATIVE", "SPIN_OFF", "SUMMARY", "COMPILATION", "CONTAINS",
        }
        media_type = m.get("type") or "ANIME"
        related_ids = []
        relations = []
        for edge in (m.get("relations") or {}).get("edges", []):
            node = edge.get("node") or {}
            # Keep franchise links within the same media type (anime↔anime, manga↔manga)
            if edge.get("relationType") in SAME_FRANCHISE_RELATIONS and node.get("type") == media_type:
                related_ids.append(node["id"])
                relations.append({
                    "source_id": node["id"],
                    "type": edge["relationType"],
                    "title": _best_title(node.get("title") or {}),
                    "poster_url": (node.get("coverImage") or {}).get("large"),
                })

        return {
            "source": self.name,
            "source_id": m["id"],
            "media_type": media_type,
            "title": main_title,
            "alt_title": alt_title,
            "year": (m.get("startDate") or {}).get("year"),
            "start_month": (m.get("startDate") or {}).get("month"),
            "start_day": (m.get("startDate") or {}).get("day"),
            "poster_url": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large"),
            "banner_url": m.get("bannerImage"),
            "description": _clean_description(m.get("description")),
            "genres": m.get("genres") or [],
            "rating": round(score / 10, 1) if score else None,
            "status": m.get("status"),
            "episodes": m.get("episodes"),
            "chapters": m.get("chapters"),
            "format": m.get("format"),
            "duration": m.get("duration"),
            "countryOfOrigin": m.get("countryOfOrigin"),
            "related_ids": related_ids,
            "relations": relations,
        }

    # -- Extra: powers Home's Trending/Top Airing feeds (not part of the shared interface) --

    def _cached(self, key: str, fetch, ttl: int | None = None):
        """L1 memory + L2 Mongo with per-entry TTL (seconds)."""
        key = f"al3:{key}"
        ttl = int(ttl if ttl is not None else CATALOG_CACHE_TTL)
        now = time.time()
        cached = self._cache.get(key)
        # tuple: (stored_at, value, entry_ttl)
        if cached and now - cached[0] < (cached[2] if len(cached) > 2 else ttl):
            return cached[1]
        try:
            from helper import database as db
            mongo_hit = db.cache_get(key)
            if mongo_hit is not None:
                self._cache[key] = (now, mongo_hit, ttl)
                return mongo_hit
        except Exception:
            pass
        value = fetch()
        self._cache[key] = (now, value, ttl)
        try:
            from helper import database as db
            db.cache_set(key, value, ttl_seconds=ttl)
        except Exception:
            pass
        return value

    def _discover(self, sort: str, page: int = 1, query: str = DISCOVER_QUERY, cache_prefix: str = "", ttl: int | None = None) -> dict:
        def fetch():
            data = self._post(query, {"sort": [sort], "page": page})
            out = []
            for m in data["Page"]["media"]:
                score = m.get("averageScore")
                full_genres = m.get("genres") or []
                tags = [t.get("name") for t in (m.get("tags") or []) if t.get("name")]
                out.append({
                    "title": _best_title(m["title"]),
                    "poster_url": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large"),
                    "rating": round(score / 10, 1) if score else None,
                    "anilist_id": m["id"],
                    "source": self.name,
                    "source_id": m["id"],
                    "media_type": "ANIME",
                    "genres": full_genres,  # full list for BL filter; trimmed after
                    "tags": tags,
                    "episodes": m.get("episodes"),
                    "synopsis": _clean_description(m.get("description"))[:140],
                })
            # Drop gay / BL / Yaoi before truncating genres for display
            out = _filter_blocked(out)
            for item in out:
                item["genres"] = (item.get("genres") or [])[:3]
                item.pop("tags", None)
            return {"results": out, "has_next": data["Page"]["pageInfo"]["hasNextPage"]}

        return self._cached(f"{cache_prefix}{sort}:{page}", fetch, ttl=ttl)

    def get_trending(self, page: int = 1) -> dict:
        # Adult anime — BL / gay filtered out after fetch
        return self._discover(
            "TRENDING_DESC", page, cache_prefix="trend-v3:",
            ttl=CATALOG_CACHE_TTL,
        )

    def get_popular(self, page: int = 1) -> dict:
        # Top Airing (currently releasing) — BL / gay filtered out
        return self._discover(
            "POPULARITY_DESC", page, query=DISCOVER_AIRING_QUERY,
            cache_prefix="airing-v3:", ttl=CATALOG_CACHE_TTL,
        )

    def get_most_popular(self, page: int = 1) -> dict:
        # Popular overall — BL / gay filtered out
        return self._discover(
            "POPULARITY_DESC", page, cache_prefix="popular-v3:",
            ttl=CATALOG_CACHE_TTL,
        )

    def _discover_manga(self, sort: str, page: int = 1, query: str = MANGA_DISCOVER_QUERY, cache_prefix: str = "manga:", ttl: int | None = None) -> dict:
        def fetch():
            data = self._post(query, {"sort": [sort], "page": page})
            out = []
            for m in data["Page"]["media"]:
                score = m.get("averageScore")
                full_genres = m.get("genres") or []
                tags = [t.get("name") for t in (m.get("tags") or []) if t.get("name")]
                out.append({
                    "title": _best_title(m["title"]),
                    "poster_url": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large"),
                    "rating": round(score / 10, 1) if score else None,
                    "anilist_id": m["id"],
                    "source": self.name,
                    "source_id": m["id"],
                    "genres": full_genres,  # full list for BL filter; trimmed after
                    "tags": tags,
                    "chapters": m.get("chapters"),
                    "format": m.get("format"),
                    "countryOfOrigin": m.get("countryOfOrigin"),
                    "media_type": "MANGA",
                    "synopsis": _clean_description(m.get("description"))[:140],
                })
            # Drop gay / BL / Yaoi before truncating genres for display
            out = _filter_blocked(out)
            for item in out:
                item["genres"] = (item.get("genres") or [])[:3]
                item.pop("tags", None)
            return {"results": out, "has_next": data["Page"]["pageInfo"]["hasNextPage"]}
        return self._cached(f"{cache_prefix}{sort}:{page}", fetch, ttl=ttl)

    def _merge_manga_pages(self, *pages: dict) -> dict:
        """Deduplicate adult manga/manhwa/doujin results from several queries."""
        seen = set()
        out = []
        has_next = False
        for page in pages:
            has_next = has_next or bool(page.get("has_next"))
            for item in page.get("results") or []:
                sid = item.get("source_id") or item.get("anilist_id")
                if sid in seen:
                    continue
                seen.add(sid)
                out.append(item)
        return {"results": out, "has_next": has_next}

    def get_trending_manga(self, page: int = 1) -> dict:
        """Trending adult manga + manhwa + doujinshi (BL/Yaoi excluded)."""
        def fetch():
            general = self._discover_manga(
                "TRENDING_DESC", page, query=MANGA_DISCOVER_QUERY,
                cache_prefix="m-trend-v3:", ttl=CATALOG_CACHE_TTL,
            )
            manhwa = self._discover_manga(
                "TRENDING_DESC", page, query=MANHWA_DISCOVER_QUERY,
                cache_prefix="m-trend-kr-v3:", ttl=CATALOG_CACHE_TTL,
            )
            # BL / Yaoi queries intentionally omitted — filtered out of discovery
            return self._merge_manga_pages(manhwa, general)
        return self._cached(
            f"manga-trend-merged-v6:{page}", fetch, ttl=CATALOG_CACHE_TTL
        )

    def get_airing_manga(self, page: int = 1) -> dict:
        """Ongoing adult manga / manhwa / doujin (BL excluded) — Top Airing row."""
        def fetch():
            general = self._discover_manga(
                "POPULARITY_DESC", page, query=MANGA_AIRING_QUERY,
                cache_prefix="m-air-v3:", ttl=CATALOG_CACHE_TTL,
            )
            # BL / Yaoi queries intentionally omitted
            return self._merge_manga_pages(general)
        return self._cached(
            f"manga-air-merged-v6:{page}", fetch, ttl=CATALOG_CACHE_TTL
        )

    def get_popular_manga(self, page: int = 1) -> dict:
        """Popular adult manga + manhwa + doujinshi (BL/Yaoi excluded)."""
        def fetch():
            general = self._discover_manga(
                "POPULARITY_DESC", page, query=MANGA_DISCOVER_QUERY,
                cache_prefix="m-pop-v3:", ttl=CATALOG_CACHE_TTL,
            )
            manhwa = self._discover_manga(
                "POPULARITY_DESC", page, query=MANHWA_DISCOVER_QUERY,
                cache_prefix="m-pop-kr-v3:", ttl=CATALOG_CACHE_TTL,
            )
            # BL / Yaoi queries intentionally omitted
            return self._merge_manga_pages(manhwa, general)
        return self._cached(
            f"manga-pop-merged-v6:{page}", fetch, ttl=CATALOG_CACHE_TTL
        )

    # Back-compat aliases used by older routes
    def get_trending_manhwa(self, page: int = 1) -> dict:
        return self.get_trending_manga(page)

    def get_popular_manhwa(self, page: int = 1) -> dict:
        return self.get_airing_manga(page)

    def search_manga(self, query: str, page: int = 1) -> dict:
        """Search ALL manga / manhwa / manhua / novels on AniList (no isAdult filter).

        Returns every matching title so pornhwa, manhwa, manhua, novels,
        and regular manga all appear in search.
        """
        results = []
        seen = set()
        has_next = False
        try:
            data = self._post(SEARCH_MANGA_BROAD_QUERY, {"search": query, "page": page})
            for m in data["Page"]["media"]:
                mid = m["id"]
                if mid in seen:
                    continue
                seen.add(mid)
                results.append(self._map_search_item(m, "MANGA"))
            has_next = data["Page"]["pageInfo"]["hasNextPage"]
        except Exception:
            pass
        return {"results": results, "has_next": has_next}

    def browse_genre(self, genre: str, page: int = 1, media_type: str = "ANIME") -> dict:
        """Browse adult titles in a genre. media_type: ANIME (H-ANIME) or MANGA (H-MANHWA)."""
        media_type = "MANGA" if str(media_type).upper() == "MANGA" else "ANIME"

        def fetch():
            data = self._post(GENRE_QUERY, {"genre": genre, "page": page, "type": media_type})
            out = []
            for m in data["Page"]["media"]:
                score = m.get("averageScore")
                out.append({
                    "title": _best_title(m["title"]),
                    "poster_url": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large"),
                    "rating": round(score / 10, 1) if score else None,
                    "anilist_id": m["id"],
                    "source": self.name,
                    "source_id": m["id"],
                    "media_type": media_type,
                })
            return {"results": out, "has_next": data["Page"]["pageInfo"]["hasNextPage"]}

        return self._cached(
            f"genre:{media_type}:{genre}:{page}",
            fetch,
            ttl=CATALOG_CACHE_TTL,
        )
