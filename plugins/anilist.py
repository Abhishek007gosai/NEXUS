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

from config import ANILIST_ENDPOINT, ANILIST_PROXY, CATALOG_CACHE_TTL
from plugins.base import AnimeSource

# Persist catalog snapshots so cold starts (Koyeb sleep/restart) still serve
# Home instantly even before a live AniList round-trip finishes.
_DISK_CACHE_DIR = Path(os.getenv("CATALOG_CACHE_DIR", "/tmp/nexus_catalog_cache"))

SEARCH_QUERY = """
query ($search: String, $page: Int) {
  Page(page: $page, perPage: 25) {
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
      status
    }
  }
}
"""


def _airing_day_from_media(m: dict) -> str | None:
    """Map AniList broadcast / next airing timestamp to sunday…saturday.

    Prefer the explicit broadcast.day (already in local schedule language).
    Fallback uses nextAiringEpisode in Asia/Tokyo so late-night JST slots
    don't shift to the previous UTC day.
    """
    day_map = {
        "sundays": "sunday", "mondays": "monday", "tuesdays": "tuesday",
        "wednesdays": "wednesday", "thursdays": "thursday",
        "fridays": "friday", "saturdays": "saturday",
        "sunday": "sunday", "monday": "monday", "tuesday": "tuesday",
        "wednesday": "wednesday", "thursday": "thursday",
        "friday": "friday", "saturday": "saturday",
    }
    b = m.get("broadcast") or {}
    raw = (b.get("day") or "").strip().lower()
    if raw in day_map:
        return day_map[raw]
    # Fallback: next episode airing time → weekday in Japan (JST)
    nae = m.get("nextAiringEpisode") or {}
    ts = nae.get("airingAt")
    if ts:
        try:
            import datetime as _dt
            # Prefer zoneinfo; fall back to fixed +09:00 if unavailable
            try:
                from zoneinfo import ZoneInfo
                d = _dt.datetime.fromtimestamp(int(ts), tz=ZoneInfo("Asia/Tokyo"))
            except Exception:
                d = _dt.datetime.utcfromtimestamp(int(ts)) + _dt.timedelta(hours=9)
            return ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][d.weekday()]
        except Exception:
            pass
    return None


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
    broadcast { day time timezone }
    nextAiringEpisode { airingAt episode }
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
  Page(page: $page, perPage: 12) {
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
  Page(page: $page, perPage: 12) {
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
  Page(page: $page, perPage: 12) {
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

    # Home feeds change slowly — keep them longer than generic search/details.
    # Soft TTL: serve from memory without refresh.
    # Hard TTL: still serve stale, but force a background refresh.
    HOME_SOFT_TTL = max(CATALOG_CACHE_TTL, 1800)       # ≥ 30 min
    HOME_HARD_TTL = max(CATALOG_CACHE_TTL * 4, 7200)    # ≥ 2 h (stale-ok)
    DEFAULT_SOFT_TTL = CATALOG_CACHE_TTL                # 10 min default
    DEFAULT_HARD_TTL = max(CATALOG_CACHE_TTL * 3, 1800)

    def __init__(self):
        # key -> (stored_at, value)
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()
        # Single-flight: one in-flight refresh per key (no stampede)
        self._inflight: dict[str, threading.Event] = {}
        try:
            _DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _ttls_for(self, key: str) -> tuple[float, float]:
        """Return (soft_ttl, hard_ttl) seconds for this cache key."""
        if key.startswith(("TRENDING", "airing:", "popular-all:")):
            return float(self.HOME_SOFT_TTL), float(self.HOME_HARD_TTL)
        return float(self.DEFAULT_SOFT_TTL), float(self.DEFAULT_HARD_TTL)

    def _disk_path(self, key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        return _DISK_CACHE_DIR / f"{safe}.json"

    def _read_disk(self, key: str):
        try:
            p = self._disk_path(key)
            if not p.is_file():
                return None
            raw = json.loads(p.read_text(encoding="utf-8"))
            # New format: {"t": epoch, "v": payload}
            if isinstance(raw, dict) and "v" in raw and isinstance(raw["v"], dict):
                return float(raw.get("t") or 0), raw["v"]
            # Legacy format: bare payload
            if isinstance(raw, dict) and "results" in raw:
                return 0.0, raw
        except Exception:
            return None
        return None

    def _write_disk(self, key: str, value: dict):
        try:
            p = self._disk_path(key)
            p.write_text(
                json.dumps({"t": time.time(), "v": value}, separators=(",", ":")),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _post(self, query: str, variables: dict) -> dict:
        # AniList rate-limits aggressively. Retry 429/5xx with backoff.
        # Optional ANILIST_PROXY routes via residential/static proxy when
        # Koyeb datacenter IPs are blocked or throttled by Cloudflare/AniList.
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        proxies = None
        if ANILIST_PROXY:
            proxies = {"http": ANILIST_PROXY, "https": ANILIST_PROXY}
        last_exc = None
        for attempt in range(4):
            try:
                resp = requests.post(
                    ANILIST_ENDPOINT,
                    json={"query": query, "variables": variables},
                    headers=headers,
                    timeout=12,
                    proxies=proxies,
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
            titles = m.get("title") or {}
            results.append({
                "source_id": m["id"],
                "anilist_id": m["id"],
                "title": _best_title(titles),
                "alt_title": titles.get("romaji") or titles.get("native"),
                "year": (m.get("startDate") or {}).get("year"),
                "poster_url": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large"),
                "rating": round(score / 10, 1) if score else None,
                "genres": (m.get("genres") or [])[:3],
                "format": m.get("format"),
                "episodes": m.get("episodes"),
                "status": m.get("status"),
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
            "airing_day": _airing_day_from_media(m),
            "related_ids": related_ids,
            "relations": relations,
        }

    # -- Extra: powers Home's Trending/Top Airing feeds (not part of the shared interface) --

    def _store(self, key: str, value: dict):
        if not value:
            return
        with self._lock:
            self._cache[key] = (time.time(), value)
        if value.get("results") is not None or value.get("title") is not None:
            self._write_disk(key, value)

    def _cached(self, key: str, fetch):
        """Optimized catalog cache:

        1. Fresh memory (age < soft TTL)  → return immediately
        2. Soft-stale memory              → return + single-flight bg refresh
        3. Disk snapshot                  → hydrate memory, return + bg refresh
        4. Cold                           → blocking fetch, then store

        Home keys use longer TTLs so Koyeb restarts / rate limits rarely
        force users to wait on live AniList.
        """
        soft_ttl, hard_ttl = self._ttls_for(key)
        now = time.time()

        with self._lock:
            cached = self._cache.get(key)
        if cached:
            age = now - cached[0]
            if age < soft_ttl:
                return cached[1]
            # Soft-stale or hard-stale: still serve, refresh in background
            if cached[1]:
                self._bg_refresh(key, fetch)
                return cached[1]

        # Cold memory → try disk (survives process restart)
        disk = self._read_disk(key)
        if disk:
            disk_t, disk_v = disk
            if disk_v:
                with self._lock:
                    # Keep original disk timestamp so soft/hard logic stays honest
                    self._cache[key] = (disk_t or (now - soft_ttl - 1), disk_v)
                age = now - (disk_t or 0)
                if age >= soft_ttl:
                    self._bg_refresh(key, fetch)
                return disk_v

        # True cold start — block on live AniList (single-flight)
        return self._blocking_fetch(key, fetch)

    def _blocking_fetch(self, key: str, fetch):
        """Ensure only one thread hits AniList for a cold key."""
        with self._lock:
            ev = self._inflight.get(key)
            if ev is None:
                ev = threading.Event()
                self._inflight[key] = ev
                leader = True
            else:
                leader = False

        if not leader:
            # Wait briefly for the leader; fall through to own fetch if timeout
            ev.wait(timeout=15)
            with self._lock:
                cached = self._cache.get(key)
            if cached and cached[1]:
                return cached[1]
            # Leader failed — try ourselves
            value = fetch()
            self._store(key, value)
            return value

        try:
            value = fetch()
            self._store(key, value)
            return value
        finally:
            with self._lock:
                self._inflight.pop(key, None)
            ev.set()

    def _bg_refresh(self, key: str, fetch):
        """Single-flight background refresh — skips if already in-flight."""
        with self._lock:
            if key in self._inflight:
                return
            ev = threading.Event()
            self._inflight[key] = ev

        def _run():
            try:
                value = fetch()
                if value:
                    self._store(key, value)
            except Exception:
                pass
            finally:
                with self._lock:
                    self._inflight.pop(key, None)
                ev.set()

        threading.Thread(target=_run, daemon=True, name=f"anilist-refresh:{key[:24]}").start()

    def warm_home(self, pages: int = 2):
        """Preload discovery feeds in parallel for faster cold start after redeploy."""
        pages = max(1, min(int(pages or 1), 3))
        jobs = []
        for p in range(1, pages + 1):
            jobs.append(("trending", p, self.get_trending))
            jobs.append(("airing", p, self.get_popular))
            jobs.append(("popular", p, self.get_most_popular))

        def _run(label, page, fn):
            try:
                fn(page)
            except Exception as e:
                print(f"[catalog] warm {label} page={page} failed: {e}")

        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=min(6, len(jobs))) as pool:
                futs = [pool.submit(_run, label, page, fn) for label, page, fn in jobs]
                for f in as_completed(futs):
                    try:
                        f.result()
                    except Exception:
                        pass
        except Exception:
            # Fallback: sequential if thread pool unavailable
            for label, page, fn in jobs:
                _run(label, page, fn)

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
