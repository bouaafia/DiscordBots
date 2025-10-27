from __future__ import annotations

import traceback
import nextcord
from nextcord.ext import commands

from utils import embeds

class ErrorHandlerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CheckFailure):
            await ctx.reply(embed=embeds.error("Permission Denied", "You do not have permission to use this command."), mention_author=False)
            return

        await ctx.reply(
            embed=embeds.error("Unexpected Error", "An unexpected error occurred. The incident was logged."),
            mention_author=False
        )
        traceback.print_exception(type(error), error, error.__traceback__)

    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: nextcord.Interaction, error: Exception):
        if isinstance(error, nextcord.ApplicationCheckFailure):
            try:
                await interaction.response.send_message(
                    embed=embeds.error("Permission Denied", "You do not have permission to use this command."),
                    ephemeral=True
                )
            except nextcord.InteractionResponded:
                await interaction.followup.send(
                    embed=embeds.error("Permission Denied", "You do not have permission to use this command."),
                    ephemeral=True
                )
            return

        try:
            await interaction.response.send_message(
                embed=embeds.error("Unexpected Error", "An unexpected error occurred. The incident was logged."),
                ephemeral=True
            )
        except nextcord.InteractionResponded:
            await interaction.followup.send(
                embed=embeds.error("Unexpected Error", "An unexpected error occurred. The incident was logged."),
                ephemeral=True
            )
        traceback.print_exception(type(error), error, error.__traceback__)

def setup(bot: commands.Bot):
    bot.add_cog(ErrorHandlerCog(bot))