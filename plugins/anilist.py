"""
AniList adapter — public GraphQL API, no API key required.
https://anilist.gitbook.io/anilist-apiv2-docs/
"""

import json
import os
import threading
import time
from pathlib import Path

import requests

from config import ANILIST_ENDPOINT, CATALOG_CACHE_TTL
from plugins.base import AnimeSource

# Persist catalog snapshots so cold starts (Koyeb sleep/restart) still serve
# Home instantly even before a live AniList round-trip finishes.
_DISK_CACHE_DIR = Path(os.getenv("CATALOG_CACHE_DIR", "/tmp/nexus_catalog_cache"))

SEARCH_QUERY = """
query ($search: String, $page: Int) {
  Page(page: $page, perPage: 15) {
    pageInfo { hasNextPage }
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      id
      title { romaji english }
      startDate { year }
      coverImage { extraLarge large }
      averageScore
      genres
      format
      episodes
    }
  }
}
"""

DETAILS_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title { romaji english }
    startDate { year month day }
    coverImage { large extraLarge }
    bannerImage
    description(asHtml: false)
    genres
    averageScore
    status
    episodes
    format
    duration
    relations {
      edges {
        relationType
        node { id type title { romaji english } coverImage { large } }
      }
    }
  }
}
"""

DISCOVER_QUERY = """
query ($sort: [MediaSort], $page: Int) {
  Page(page: $page, perPage: 10) {
    pageInfo { hasNextPage }
    media(type: ANIME, sort: $sort) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      genres
      episodes
      description(asHtml: false)
    }
  }
}
"""

# Same shape as DISCOVER_QUERY, but restricted to anime that is actually
# still airing right now — used for the "Top Airing" feed so finished
# shows (e.g. Death Note) don't show up just because they're popular.
DISCOVER_AIRING_QUERY = """
query ($sort: [MediaSort], $page: Int) {
  Page(page: $page, perPage: 10) {
    pageInfo { hasNextPage }
    media(type: ANIME, sort: $sort, status: RELEASING) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
      genres
      episodes
      description(asHtml: false)
    }
  }
}
"""

GENRE_QUERY = """
query ($genre: String, $page: Int) {
  Page(page: $page, perPage: 10) {
    pageInfo { hasNextPage }
    media(type: ANIME, genre: $genre, sort: POPULARITY_DESC) {
      id
      title { romaji english }
      coverImage { extraLarge large }
      averageScore
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


class AniListSource(AnimeSource):
    name = "anilist"

    def __init__(self):
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()
        try:
            _DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _disk_path(self, key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        return _DISK_CACHE_DIR / f"{safe}.json"

    def _read_disk(self, key: str):
        try:
            p = self._disk_path(key)
            if not p.is_file():
                return None
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "results" in data:
                return data
        except Exception:
            return None
        return None

    def _write_disk(self, key: str, value: dict):
        try:
            p = self._disk_path(key)
            p.write_text(json.dumps(value), encoding="utf-8")
        except Exception:
            pass

    def _post(self, query: str, variables: dict) -> dict:
        # AniList rate-limits aggressively. Retry 429/5xx with backoff.
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; NexusAnimeIndex/1.0)",
        }
        last_exc = None
        for attempt in range(4):
            try:
                resp = requests.post(
                    ANILIST_ENDPOINT,
                    json={"query": query, "variables": variables},
                    headers=headers,
                    timeout=12,
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
                try:
                    delay = float(retry_after) if retry_after else 1.2 * (attempt + 1)
                except (TypeError, ValueError):
                    delay = 1.2 * (attempt + 1)
                time.sleep(min(delay, 8))
                continue
            if resp.status_code >= 500:
                last_exc = requests.HTTPError(
                    f"{resp.status_code} server error (attempt {attempt + 1})", response=resp
                )
                time.sleep(0.6 * (attempt + 1))
                continue
            try:
                resp.raise_for_status()
                payload = resp.json()
            except Exception as e:
                last_exc = e
                time.sleep(0.4 * (attempt + 1))
                continue
            if payload.get("errors") and not payload.get("data"):
                last_exc = RuntimeError(str(payload["errors"][:1]))
                time.sleep(0.4 * (attempt + 1))
                continue
            data = payload.get("data")
            if data is None:
                last_exc = RuntimeError("AniList returned empty data")
                time.sleep(0.4 * (attempt + 1))
                continue
            return data
        if last_exc:
            raise last_exc
        raise RuntimeError("AniList request failed")

    def search(self, query: str, page: int = 1) -> dict:
        data = self._post(SEARCH_QUERY, {"search": query, "page": page})
        media = data["Page"]["media"]
        results = []
        for m in media:
            score = m.get("averageScore")
            results.append({
                "source_id": m["id"],
                "anilist_id": m["id"],
                "title": _best_title(m["title"]),
                "year": (m.get("startDate") or {}).get("year"),
                "poster_url": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large"),
                "rating": round(score / 10, 1) if score else None,
                "genres": (m.get("genres") or [])[:3],
                "format": m.get("format"),
                "episodes": m.get("episodes"),
            })
        return {"results": results, "has_next": data["Page"]["pageInfo"]["hasNextPage"]}

    def get_details(self, source_id, use_cache: bool = True) -> dict:
        if use_cache:
            return self._cached(f"details:{source_id}", lambda: self._fetch_details(source_id))
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
        related_ids = []
        relations = []
        for edge in (m.get("relations") or {}).get("edges", []):
            node = edge.get("node") or {}
            if edge.get("relationType") in SAME_FRANCHISE_RELATIONS and node.get("type") == "ANIME":
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
            "format": m.get("format"),
            "duration": m.get("duration"),
            "related_ids": related_ids,
            "relations": relations,
        }

    # -- Extra: powers Home's Trending/Top Airing feeds (not part of the shared interface) --

    def _cached(self, key: str, fetch):
        """Memory → disk → live AniList. Stale entries are returned instantly
        while a background refresh runs (stale-while-revalidate)."""
        now = time.time()
        with self._lock:
            cached = self._cache.get(key)
        if cached:
            age = now - cached[0]
            if age < CATALOG_CACHE_TTL:
                return cached[1]
            # Stale memory — serve it and refresh in background
            self._bg_refresh(key, fetch)
            return cached[1]

        # Cold memory: try disk snapshot from previous process
        disk = self._read_disk(key)
        if disk and disk.get("results"):
            with self._lock:
                self._cache[key] = (now - CATALOG_CACHE_TTL - 1, disk)  # mark stale
            self._bg_refresh(key, fetch)
            return disk

        # True cold start — must hit AniList
        value = fetch()
        with self._lock:
            self._cache[key] = (time.time(), value)
        if value and value.get("results"):
            self._write_disk(key, value)
        return value

    def _bg_refresh(self, key: str, fetch):
        def _run():
            try:
                value = fetch()
                if value and value.get("results"):
                    with self._lock:
                        self._cache[key] = (time.time(), value)
                    self._write_disk(key, value)
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()

    def _discover(self, sort: str, page: int = 1, query: str = DISCOVER_QUERY, cache_prefix: str = "") -> dict:
        def fetch():
            data = self._post(query, {"sort": [sort], "page": page})
            out = []
            for m in data["Page"]["media"]:
                score = m.get("averageScore")
                out.append({
                    "title": _best_title(m["title"]),
                    "poster_url": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large"),
                    "rating": round(score / 10, 1) if score else None,
                    "anilist_id": m["id"],
                    "genres": (m.get("genres") or [])[:3],
                    "episodes": m.get("episodes"),
                    "synopsis": _clean_description(m.get("description"))[:140],
                })
            return {"results": out, "has_next": data["Page"]["pageInfo"]["hasNextPage"]}

        return self._cached(f"{cache_prefix}{sort}:{page}", fetch)

    def get_trending(self, page: int = 1) -> dict:
        return self._discover("TRENDING_DESC", page)

    def get_popular(self, page: int = 1) -> dict:
        # Backs the "Top Airing" section — must only include anime that is
        # currently releasing, not just anime that is popular overall.
        return self._discover("POPULARITY_DESC", page, query=DISCOVER_AIRING_QUERY, cache_prefix="airing:")

    def get_most_popular(self, page: int = 1) -> dict:
        # Backs the "Popular" section — most popular anime overall,
        # regardless of airing status (unlike get_popular/"Top Airing").
        return self._discover("POPULARITY_DESC", page, cache_prefix="popular-all:")

    def browse_genre(self, genre: str, page: int = 1) -> dict:
        def fetch():
            data = self._post(GENRE_QUERY, {"genre": genre, "page": page})
            out = []
            for m in data["Page"]["media"]:
                score = m.get("averageScore")
                out.append({
                    "title": _best_title(m["title"]),
                    "poster_url": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large"),
                    "rating": round(score / 10, 1) if score else None,
                    "anilist_id": m["id"],
                })
            return {"results": out, "has_next": data["Page"]["pageInfo"]["hasNextPage"]}

        return self._cached(f"genre:{genre}:{page}", fetch)
