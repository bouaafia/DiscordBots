import datetime
import nextcord

ACCENT = nextcord.Colour.blurple()
SUCCESS = nextcord.Colour.green()
ERROR = nextcord.Colour.red()
WARN = nextcord.Colour.gold()

BOT_FOOTER = "Reaction Roles • Powered by Nextcord"

def base(title: str | None = None, description: str | None = None, color: nextcord.Colour = ACCENT) -> nextcord.Embed:
    emb = nextcord.Embed(
        title=title or nextcord.Embed.Empty,
        description=description or nextcord.Embed.Empty,
        color=color,
        timestamp=datetime.datetime.utcnow()
    )
    emb.set_footer(text=BOT_FOOTER)
    return emb

def info(title: str, description: str) -> nextcord.Embed:
    return base(title, description, ACCENT)

def success(title: str, description: str) -> nextcord.Embed:
    return base(title, description, SUCCESS)

def warn(title: str, description: str) -> nextcord.Embed:
    return base(title, description, WARN)

def error(title: str, description: str) -> nextcord.Embed:
    return base(title, description, ERROR)