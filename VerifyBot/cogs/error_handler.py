import traceback
import logging
import nextcord
from nextcord.ext import commands
from nextcord import Interaction

logger = logging.getLogger(__name__)
RED = nextcord.Color.red()

class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("ErrorHandler cog initialized")

    @staticmethod
    async def _reply_interaction_error(interaction: Interaction, title: str, description: str):
        embed = nextcord.Embed(title=title, description=description, color=RED)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error: Exception):
        friendly = "An error occurred while processing your request."
        if isinstance(error, nextcord.ApplicationCheckFailure):
            friendly = "You do not have permission to use this command."
        elif isinstance(error, nextcord.HTTPException):
            friendly = "I couldn't complete that action due to a Discord API error."

        await self._reply_interaction_error(
            interaction,
            title="Error",
            description=friendly
        )

        logger.error("Application command error: %s", error)
        traceback.print_exception(type(error), error, error.__traceback__)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        embed = nextcord.Embed(
            title="Error",
            description="An error occurred while processing your command.",
            color=RED
        )
        try:
            await ctx.send(embed=embed)
        except Exception:
            pass
        logger.error("Prefix command error: %s", error)
        traceback.print_exception(type(error), error, error.__traceback__)

def setup(bot: commands.Bot):
    bot.add_cog(ErrorHandler(bot))