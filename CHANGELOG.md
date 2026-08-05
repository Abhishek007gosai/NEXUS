# Changelog

## v2.1.0 — Unified structure (Nexus + Anime Index)

Project layout matches the integrated **NEXUS-Kaya** layout:

```
├── main.py              # entry — Flask thread + Pyrogram
├── bot.py               # Bot client; hosts Flask app
├── config.py            # unified config
├── helper/
│   └── database.py      # file-store (motor) + anime catalog (pymongo)
└── plugins/
    ├── index.py         # /anidex, library search, request callbacks
    ├── anilist.py / base.py
    ├── web/             # Mini App static files
    │   ├── index.html
    │   ├── app.js
    │   └── style.css
    └── start, shortner, settings, …
```

### One bot
- **Pyrogram** — file store (deep links, force-sub, shortener, premium)
- **Flask (`app.py`)** — Mini App UI + `/api/*` on `$PORT`
- **Shared MongoDB** — users/channels/pros + anime/requests/reports

### Anime Index
- Franchise Prequel/Sequel navigation (release order, max 2 cards)
- Requests with Accept/Reject + reason submenu in log channel
- Notification bell in Mini App
- Private text search of Available library (auto-delete 2 min)
- Franchise-wide auto-link when setting a join link
- Admin ➕ link editor in Mini App

### File Store
- Multi force-sub, auto-delete, multi DB channels
- Shortener gate, premium, ban/unban, broadcast

### Layout note
- Root `app.py` moved into **`plugins/index.py`** (Flask Mini App + Pyrogram handlers together).

- Split: **app.py** = Flask Mini App; **plugins/index.py** = Pyrogram handlers (index_bot).
