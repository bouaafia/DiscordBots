# Discord Verification Bot (nextcord, cogs, embeds-only, application emojis)

This bot uses nextcord with a cog structure and embeds-only messaging. It creates and uses only application emojis via `await bot.create_application_emoji()` — no guild emoji fallback.

Features
- Slash command: `/setupverification`
  - Options: `verifiedrole`, `notverifiedrole`, `channelofverification`
- On member join: assigns `notverifiedrole` (humans only) and DMs an embed guiding them to the verification channel
- Posts an embed with a persistent "Verify" button
- Clicking "Verify":
  - Generates a random captcha (text or math), rendered as an image
  - A "Solve" button (with application emoji) opens a modal to enter the answer
  - Up to 5 attempts; challenge expires after 10 minutes
  - On success, adds `verifiedrole` and removes `notverifiedrole`
- Emoji management (application emojis only)
  - Config file at `config/config.json` with URLs for the Verify and Solve button emojis
  - On startup, the bot creates application emojis via `await bot.create_application_emoji()` and stores IDs in the same config
  - Buttons use these emojis if available (if creation fails or API unsupported, buttons work without emojis)
- Admin tooling
  - `/refresh_emojis` — re-checks and creates application emojis from config
- Embeds-only for user messages
- Logging for startup, emoji creation, and verification steps
- Background task cleans expired challenges

Prerequisites
- Python 3.10+ recommended
- Discord bot with Server Members Intent enabled
- Invite bot with scopes: `bot`, `applications.commands`
- Permissions:
  - Manage Roles (and bot role above target roles)
  - Send Messages and Embed Links in the verification channel

Setup
1. Create and activate a virtual environment, then install:
   ```bash
   python -m venv .venv
   . .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and set `DISCORD_TOKEN`. Optionally set `GUILD_ID` for faster command registration during development.
3. Start the bot:
   ```bash
   python bot.py
   ```
4. In your server, run:
   ```
   /setupverification verifiedrole:@Verified notverifiedrole:@NotVerified channelofverification:#verification
   ```

Emoji configuration
- The global emoji config is in `config/config.json`. Defaults:
  - Verify: https://cdn3.emoji.gg/emojis/2155-verify-green.gif
  - Solve: https://cdn3.emoji.gg/emojis/3863_gearz.gif
- On startup, the bot attempts to create application emojis from these URLs via `create_application_emoji` and stores their IDs in the same file.
- If your nextcord version does not support `create_application_emoji`, the bot logs an error and emojis will not appear on the buttons (but everything else works). No guild emojis will be created.

Troubleshooting
- If commands don’t show:
  - Ensure the bot is invited with `applications.commands`.
  - If `GUILD_ID` is set, commands appear only in that guild; remove it for global registration (global can take up to ~1 hour).
- If `Emoji Refresh Failed` occurs:
  - Upgrade nextcord to a version that supports `create_application_emoji`.
  - Ensure the emoji URLs are valid and reachable.
- If roles aren’t applied:
  - Ensure the bot has `Manage Roles` and is placed above the target roles.