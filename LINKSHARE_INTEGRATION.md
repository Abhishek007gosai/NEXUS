# Link Share integration

The permanent MongoDB-backed Link Share menu is implemented in `plugins/linkshare.py`.

The menu is intended to be opened from the bot's Settings menu with callback data `ls_menu`.
It provides:
- Normal Links: channel-name URL buttons
- Request Links: channel-name URL buttons
- List Channels
- Back

Link Share records are stored in MongoDB and use permanent tokens. This is separate
from File Store persistence, which remains restricted to `/genlink` and `/batch`.
