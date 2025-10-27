from __future__ import annotations

import nextcord
from nextcord.ext import commands

from utils.storage import get_message_mapping
from utils.embeds import error as error_embed

def key_from_payload(emoji: nextcord.PartialEmoji) -> str:
    if emoji.id:
        return f"e:{emoji.id}"
    return f"u:{emoji.name}"

class ReactionRolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: nextcord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        data = get_message_mapping(payload.message_id)
        if not data:
            return

        # Ignore cross-guild (shouldn't happen) or DMs
        if payload.guild_id != data.get("guild_id"):
            return

        # Determine role from mapping
        key = key_from_payload(payload.emoji)
        role_id = data.get("mappings", {}).get(key)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if guild is None:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            # fetch fallback
            try:
                member = await guild.fetch_member(payload.user_id)
            except Exception:
                return

        role = guild.get_role(int(role_id))
        if role is None:
            return

        # Assign role if not already has
        if role in member.roles:
            return

        try:
            await member.add_roles(role, reason=f"Reaction role via message {payload.message_id}")
        except nextcord.Forbidden:
            # Try DM user with a friendly embed (best-effort)
            try:
                await member.send(embed=error_embed(
                    "Role Assignment Failed",
                    f"I couldn't assign the role {role.mention} due to missing permissions. "
                    f"Please ask an admin to ensure my top role is higher than {role.mention} and I have 'Manage Roles'."
                ))
            except Exception:
                pass
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: nextcord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        data = get_message_mapping(payload.message_id)
        if not data:
            return

        if payload.guild_id != data.get("guild_id"):
            return

        key = key_from_payload(payload.emoji)
        role_id = data.get("mappings", {}).get(key)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if guild is None:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            # fetch fallback
            try:
                member = await guild.fetch_member(payload.user_id)
            except Exception:
                return

        role = guild.get_role(int(role_id))
        if role is None:
            return

        # Remove role if present
        if role not in member.roles:
            return

        try:
            await member.remove_roles(role, reason=f"Reaction role removal via message {payload.message_id}")
        except Exception:
            pass

def setup(bot: commands.Bot):
    bot.add_cog(ReactionRolesCog(bot))