# NEXUS-ECCHI

**One bot** that combines:

1. **File Store Pro** — share files via deep links, force-sub, shortener, auto-delete, premium
2. **EcchiDex Anime Index** — Telegram Mini App to browse AniList adult anime/manhwa, request titles, set join links

## Features

### File Store
- Multi force-sub (request-join supported)
- Auto-delete + retrieve link
- URL shortener gate for free users
- Premium users, ban/unban, broadcast
- Multi DB channels

### Anime Index Mini App
- Home: Trending / Top Airing / Popular (H-Anime + H-Manhwa)
- Available library A–Z with join links
- Search + genre browse (AniList)
- Request system with Accept/Reject in log channel
- Admin ➕ link editor (franchise-wide auto-link)
- Profile + notification bell
- Bot: `/anidex` opens mini app · plain text searches library

## Environment

See `.env.example`. Required:

| Variable | Purpose |
|----------|---------|
| `TOKEN` / `BOT_TOKEN` | Bot token from @BotFather |
| `API_ID` / `API_HASH` | from my.telegram.org |
| `DB_URI` | MongoDB connection string |
| `DB_CHANNEL` | Channel where files are stored |
| `OWNER_ID` / `ADMINS` | Admin Telegram user IDs |
| `WEBAPP_URL` | Public HTTPS URL of this deployment (for Mini App) |
| `LOG_CHANNEL_ID` | Channel for request/report notifications |

## Run locally

```bash
pip install -r requirements.txt
# fill .env or export vars
python main.py
```

For the Mini App locally, tunnel with ngrok and set `WEBAPP_URL=https://xxx.ngrok.io`.

## Deploy (Render / Koyeb)

1. Push repo to GitHub
2. Create Web Service from Dockerfile
3. Set env vars (especially `TOKEN`, `DB_URI`, `WEBAPP_URL`, `LOG_CHANNEL_ID`)
4. After first deploy, set `WEBAPP_URL` to the real `*.onrender.com` / `*.koyeb.app` URL and redeploy

Bot uses **polling** (Pyrogram). Flask serves `/` (mini app) + `/api/*` + `/health` on `$PORT`.

## Commands

| Command | Who | Description |
|---------|-----|-------------|
| `/start` | all | Welcome / file deep-links |
| `/anidex` | all | Open Anime Index mini app |
| *(any text)* | private | Search Available library |
| `/settings` | admin | File-store settings |
| `/shortner` | admin | Shortener config |
| `/request` | premium | Request content (file-store) |

## Project layout

```
main.py          entry — Flask thread + Pyrogram
bot.py           Bot client + Flask host
miniapp.py       Anime Index Flask API + pages
config.py        unified config
helper/          MongoDB (file-store + catalog_db)
plugins/         Pyrogram plugins + anilist + index_bot
web/             Mini App (HTML/CSS/JS)
```


## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full history.

### v3.0.0 — Unified bot
- **One process:** File Store (Pyrogram) + Anime Index Mini App (Flask) + shared MongoDB.
- **`/anidex`** opens the Mini App; private text searches the Available library (replies auto-delete after 2 min).
- **Requests** with Accept/Reject in the log channel (quick reasons); notification bell in the app.
- **Franchise nav:** at most Prequel + Sequel cards in release order.
- **Franchise-wide auto-link:** linking one title pulls related seasons/OVAs/movies from AniList.

## License

GPL-3.0 (see LICENSE). File-store base by Codeflix/BotifyX; Anime Index integration included.
