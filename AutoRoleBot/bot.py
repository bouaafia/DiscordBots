import os
import logging
from pathlib import Path

import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("reaction-roles-bot")

# Intents
intents = nextcord.Intents.default()
intents.guilds = True
intents.members = True
intents.reactions = True
# message_content not required for slash + reactions
intents.message_content = False

# Bot
bot = commands.Bot(
    intents=intents
)

COGS = [
    "cogs.setup",
    "cogs.react_roles",
    "cogs.error_handler",
]

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    

def main():
    # Ensure data dir exists
    Path("data").mkdir(parents=True, exist_ok=True)

    # Load cogs
    for cog in COGS:
        try:
            bot.load_extension(cog)
            logger.info(f"Loaded extension: {cog}")
        except Exception as e:
            logger.exception(f"Failed to load extension {cog}: {e}")

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN is not set. Put it in your environment or .env file.")
        return
    bot.run(token)

if __name__ == "__main__":
    main()