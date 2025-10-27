# 🎭 Reaction Roles Bot (Nextcord)

A clean, embed-only Discord bot for reaction roles with an admin-only setup flow, templates, and error handling — built with Nextcord and Cogs.

## ✨ Features
- 🧪 Reaction roles: add reaction → get role, remove reaction → remove role
- 🛡️ Admin-only slash command: `/setup`
- 🧰 Interactive builder: button → modal (no plain messages)
- 🎨 Templates with previews and aesthetic embeds
- 🙂 Flexible emoji input:
  - `<:name:id>:role_id`, `emoji_id:role_id`, `😀:role_id`
  - Name-only: `:name::role_id` or `<:name:>:role_id` (auto-resolves in the server)
- 🧱 Robust error handling and friendly feedback
- 💾 Simple JSON persistence (data/role_messages.json)

## 🧩 Project Structure
```text
.
├── bot.py
├── requirements.txt
├── .env.example
├── utils/
│   ├── embeds.py
│   └── storage.py
├── cogs/
│   ├── setup.py
│   ├── react_roles.py
│   └── error_handler.py
└── data/
    └── role_messages.json (auto-created)
```

## 📦 Install
1) Python 3.11 or 3.12 recommended  
2) Install dependencies:
```bash
pip install -r requirements.txt
```

## ⚙️ Configure
1) Create a bot in the Discord Developer Portal and copy its token  
2) Copy `.env.example` to `.env` and set:
```env
DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
```
3) Invite the bot with:
- scopes: `bot applications.commands`
- permissions: Manage Roles, Add Reactions, Read Message History, Send Messages, View Channels

Tip: Place the bot’s top role above all roles it needs to assign.

## ▶️ Run
```bash
python bot.py
```

## 🛠️ Usage: /setup Flow
1) Admin runs `/setup`
2) Pick a template (you’ll see an ephemeral preview)
3) Click “Open Builder” → fill the modal:
   - Title (optional; uses template if blank)
   - Message Body (optional; uses template if blank)
   - Emoji ↔ Role pairs (required)
   - Target channel mention or ID (required)
4) Submit — bot posts the embed in the chosen channel, adds reactions, and wires role logic

The posted embed includes a clean legend like:
```
• 😀 → @Member
• 🔔 → @Announcements
• <:custom:123...> → @Exclusive
```

## 🧪 Emoji ↔ Role Input Formats
Enter one mapping per line:
```
<:name:id>:role_id
emoji_id:role_id
😀:role_id
:name::role_id          # resolves by name in your server
<:name:>:role_id        # resolves by name in your server
```

How to get IDs:
- Emoji ID: type a backslash before sending the emoji: `\:your_emoji:` → Discord shows `<:name:1234567890>`
- Role ID: enable Developer Mode → right-click role mention → Copy ID

## 🎨 Templates
Built-in templates with previews:
- Minimal
- Notifications
- Game Roles
- Pronouns

If you leave Title or Message blank in the modal, the selected template’s defaults are used automatically.

## 🔐 Permissions Checklist
- Bot has Manage Roles
- Bot’s top role is above target roles
- Bot can View Channel and Send Messages in the target channel
- For custom emojis, the emoji must be available to the bot (usually from the same server)

## 🧰 Troubleshooting
- 404 Unknown application command during sync:
  - Handled by manually syncing on ready. If you’re on Python 3.13, consider 3.11–3.12 or keep Nextcord updated.
- Modal “Invalid Form Body … placeholder must be ≤ 100”:
  - All placeholders are short; if you edit them, keep each ≤ 100 chars.
- Reactions don’t appear:
  - Ensure the emoji exists in the server and the bot can use it
  - For custom emojis, use exact ID or a unique name resolvable in your server

---

Built with ❤️ using Nextcord and embeds-only UI.
