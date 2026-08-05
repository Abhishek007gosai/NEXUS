# Changelog

## v3.0.0 — Unified bot (NEXUS + EcchiDex)

File Store Pro and EcchiDex Anime Index now run as **one process**:

- **Pyrogram** handles file-store (deep links, force-sub, shortener, premium, admin settings).
- **Flask** serves the Mini App (`web/`) and JSON API (`/api/*`) on `$PORT`.
- **Shared MongoDB** — file-store collections + anime catalog (`anime`, `requests`, `reports`, …).
- **`/anidex`** opens the Mini App; plain text in private chat searches the Available library.
- Request Accept / Reject buttons work in the log channel via Pyrogram callbacks.
- Single `config.py` / `.env` for both stacks (`TOKEN`, `DB_URI`, `WEBAPP_URL`, `LOG_CHANNEL_ID`, …).

### Anime Index (from EcchiDex)

#### Franchise navigation (Prequel / Sequel)
A title’s detail sheet shows **at most two** related-title cards — Prequel and Sequel — walking the full franchise (seasons, OVA, movie, spin-off) in release order instead of one card per AniList relation edge.

- `plugins/anilist.py` — fetches month/day with year for correct same-year sorting.
- `helper/catalog_db.py` — `get_franchise_neighbors()` builds the timeline and returns only previous/next posted entries.

#### Requests (replaces Votes)
Requesting a title that isn’t posted creates a real request admins can act on.

- `requests` collection: create, list pending, accept/reject with reasons, notifications.
- Setting a join link on a title auto-accepts matching pending requests.
- Log channel: Accept / Reject with quick-reason submenu (already posted, not available, not released, other).

#### Notification bell
Bell in the Mini App header shows when the user’s requests are resolved (accepted / rejected + note).

#### Bot text search
- Private chats only.
- Replies (no match, multi-match picker, single result) auto-delete after **2 minutes**.

#### Franchise-wide auto-linking
Setting a join link walks the AniList relation graph live: updates posted titles and creates+links unposted seasons/OVAs/movies. Clearing a link removes the unlinked family from MongoDB.

### File Store (NEXUS baseline)
- Multi force-sub (request-join), auto-delete, content buttons, protect content.
- URL shortener gate for free users; premium bypass.
- Multi DB channels, ban/unban, broadcast, admin settings UI.

## Earlier EcchiDex notes

- `/anidex` welcome with Open Mini App button; `/start` left to file-store.
- Home: All / Available; Trending, Top Airing, Popular; H-ANIME + H-MANHWA.
- Admin ➕ link editor is the only way to add/edit/remove catalog posts (no `/addpost` bot commands).
