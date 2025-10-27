import logging
import os

from dotenv import load_dotenv
import nextcord
from nextcord.ext import commands

from utils.emoji_manager import ensure_application_emojis, load_global_config

load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("nextcord").setLevel(logging.INFO)
logger = logging.getLogger("bot")


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in environment")

intents = nextcord.Intents.default()
intents.members = True  # required to receive on_member_join
intents.all()
bot = commands.Bot(intents=intents, help_command=None)


def load_all_cogs(bot: commands.Bot, cogs_dir: str = "cogs"):
    logger.info("Loading cogs from: %s", cogs_dir)
    if not os.path.isdir(cogs_dir):
        logger.warning("Cogs directory '%s' does not exist; skipping.", cogs_dir)
        return

    for filename in os.listdir(cogs_dir):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        ext = f"{cogs_dir.replace(os.sep, '.')}.{filename[:-3]}"
        try:
            bot.load_extension(ext)
            logger.info("Loaded cog: %s", ext)
        except Exception as e:
            logger.exception("Failed to load cog %s: %s", ext, e)

@bot.event
async def on_ready():
    logger.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    try:
        await bot.change_presence(
            status=nextcord.Status.online,
            activity=nextcord.Game("/setupverification • /refresh_emojis"),
        )
    except Exception:
        pass

    
    try:
        await ensure_application_emojis(bot)
    except Exception as e:
        logger.exception("ensure_application_emojis failed: %s", e)

    


def main():
    cfg = load_global_config()
    logger.info("Global config loaded. Emoji URLs: %s", cfg.get("emoji_urls"))

    load_all_cogs(bot, "cogs")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()