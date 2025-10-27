import logging
import time
from io import BytesIO

import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction, SlashOption, ChannelType, Permissions
from nextcord.ui import View, Modal, TextInput
from nextcord import ButtonStyle, Embed, File, ui

from utils.config_store import get_guild_config, set_guild_config
from utils.challenges import (
    get_or_create_active_challenge,
    clear_challenge,
    challenges,
    CHALLENGE_TTL_MINUTES,
)
from utils.emoji_manager import get_button_emoji

logger = logging.getLogger(__name__)

GREEN = nextcord.Color.green()
BLUE = nextcord.Color.blurple()
ORANGE = nextcord.Color.orange()
RED = nextcord.Color.red()

VERIFY_COOLDOWN_S = 4
last_verify_click_ts: dict[int, float] = {}  # user_id -> last click

async def send_embed_interaction(
    interaction: Interaction,
    embed: Embed,
    ephemeral: bool = True,
    file: File | None = None,
    view: View | None = None
):
    kwargs: dict = {"embed": embed, "ephemeral": ephemeral}
    if file is not None:
        kwargs["files"] = [file]
    if view is not None:
        kwargs["view"] = view

    if not interaction.response.is_done():
        await interaction.response.send_message(**kwargs)
    else:
        await interaction.followup.send(**kwargs)

class SolveModal(Modal):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__(title="Solve Verification Challenge", custom_id="verify:modal")
        self.guild_id = guild_id
        self.user_id = user_id
        self.answer_input = TextInput(
            label="Your answer",
            placeholder="Enter exactly what you see, or the math result",
            required=True,
            min_length=1,
            max_length=16
        )
        self.add_item(self.answer_input)

    async def callback(self, interaction: Interaction):
        ch = challenges.get((self.guild_id, self.user_id))
        if ch is None or ch.is_expired():
            clear_challenge(self.guild_id, self.user_id)
            embed = Embed(
                title="Challenge Expired",
                description="Your challenge expired. Click Verify again to get a new one.",
                color=ORANGE
            )
            await send_embed_interaction(interaction, embed, ephemeral=True)
            return

        given = self.answer_input.value.strip().upper()
        expected = ch.answer.strip().upper()

        if given == expected:
            clear_challenge(self.guild_id, self.user_id)
            guild = interaction.guild
            if guild is None:
                embed = Embed(title="Error", description="Could not find guild context.", color=RED)
                await send_embed_interaction(interaction, embed, ephemeral=True)
                return

            cfg = get_guild_config(guild.id)
            if not cfg:
                embed = Embed(title="Not Configured", description="Verification isn't set up in this server.", color=RED)
                await send_embed_interaction(interaction, embed, ephemeral=True)
                return

            member = guild.get_member(self.user_id) or await guild.fetch_member(self.user_id)
            verified_role = guild.get_role(cfg["verified_role_id"])
            not_verified_role = guild.get_role(cfg["not_verified_role_id"])

            added_text = ""
            removed_text = ""

            if verified_role:
                try:
                    await member.add_roles(verified_role, reason="Verification success")
                    added_text = f"Granted {verified_role.mention}."
                except Exception as e:
                    logger.warning("Failed to add verified role: %s", e)
                    added_text = "Tried to grant the verified role but lacked permission."

            if not_verified_role:
                try:
                    await member.remove_roles(not_verified_role, reason="Verification success")
                    removed_text = f"Removed {not_verified_role.mention}."
                except Exception as e:
                    logger.warning("Failed to remove not-verified role: %s", e)
                    removed_text = "Tried to remove the not-verified role but lacked permission."

            embed = Embed(
                title="You are verified!",
                description=f"{added_text} {removed_text}".strip(),
                color=GREEN
            )
            await send_embed_interaction(interaction, embed, ephemeral=True)
            logger.info("User %s verified in guild %s", member.id, guild.id)
            return

        ch.attempts_left -= 1
        if ch.attempts_left <= 0:
            clear_challenge(self.guild_id, self.user_id)
            embed = Embed(
                title="Challenge Failed",
                description="Incorrect answer. You have used all 5 attempts. Click Verify to start a new challenge.",
                color=RED
            )
            await send_embed_interaction(interaction, embed, ephemeral=True)
            logger.info("User %s failed verification in guild %s (attempts exhausted)", self.user_id, self.guild_id)
        else:
            view = SolveView(self.guild_id, self.user_id)
            file = File(BytesIO(ch.image_bytes), filename="challenge.png")
            embed = Embed(
                title="Verification Challenge",
                description=f"Incorrect. Attempts left: {ch.attempts_left}\nSolve the same challenge.",
                color=ORANGE
            )
            embed.set_image(url="attachment://challenge.png")
            await send_embed_interaction(interaction, embed, ephemeral=True, file=file, view=view)
            logger.info("User %s incorrect answer, attempts left=%s (guild %s)", self.user_id, ch.attempts_left, self.guild_id)

class SolveView(View):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.user_id = user_id

        btn = ui.Button(
            label="Solve",
            style=ButtonStyle.primary,
            custom_id="verify:solve",
            emoji=get_button_emoji("solve")
        )
        async def _cb(interaction: Interaction):
            await interaction.response.send_modal(SolveModal(self.guild_id, self.user_id))
        btn.callback = _cb
        self.add_item(btn)

class PersistentVerificationView(View):
    """
    Persistent view registered at startup so custom_id keeps working after restarts.
    Emoji application here is optional (the panel posting will have the emoji).
    """
    def __init__(self):
        super().__init__(timeout=None)

        btn = ui.Button(
            label="Verify",
            style=ButtonStyle.success,
            custom_id="verify:start",
            emoji=get_button_emoji("verify")
        )
        async def _cb(interaction: Interaction):
            await handle_start_verify(interaction)
        btn.callback = _cb
        self.add_item(btn)

class PanelViewWithEmoji(View):
    """
    Non-persistent view used when posting the panel, with the application emoji applied.
    """
    def __init__(self):
        super().__init__(timeout=None)

        btn = ui.Button(
            label="Verify",
            style=ButtonStyle.success,
            custom_id="verify:start",
            emoji=get_button_emoji("verify")
        )
        async def _cb(interaction: Interaction):
            await handle_start_verify(interaction)
        btn.callback = _cb
        self.add_item(btn)

async def handle_start_verify(interaction: Interaction):
    now = time.time()
    last = last_verify_click_ts.get(interaction.user.id, 0.0)
    if now - last < VERIFY_COOLDOWN_S:
        left = int(VERIFY_COOLDOWN_S - (now - last))
        left = max(left, 1)
        embed = Embed(
            title="Slow down",
            description=f"Please wait {left}s before trying again.",
            color=ORANGE
        )
        await send_embed_interaction(interaction, embed, ephemeral=True)
        return
    last_verify_click_ts[interaction.user.id] = now

    guild = interaction.guild
    if guild is None:
        embed = Embed(title="Server Only", description="This can only be used inside a server.", color=RED)
        await send_embed_interaction(interaction, embed, ephemeral=True)
        return

    cfg = get_guild_config(guild.id)
    if not cfg:
        embed = Embed(title="Not Configured", description="Verification isn't set up in this server.", color=RED)
        await send_embed_interaction(interaction, embed, ephemeral=True)
        return

    member = interaction.user if isinstance(interaction.user, nextcord.Member) else guild.get_member(interaction.user.id)
    if member is None:
        embed = Embed(title="Error", description="Could not resolve your member record.", color=RED)
        await send_embed_interaction(interaction, embed, ephemeral=True)
        return

    verified_role = guild.get_role(cfg["verified_role_id"])
    not_verified_role = guild.get_role(cfg["not_verified_role_id"])

    if verified_role and verified_role in member.roles:
        if not_verified_role and not_verified_role in member.roles:
            try:
                await member.remove_roles(not_verified_role, reason="Already verified")
            except Exception:
                pass
        embed = Embed(title="Already Verified", description="You are already verified.", color=GREEN)
        await send_embed_interaction(interaction, embed, ephemeral=True)
        return

    ch = get_or_create_active_challenge(guild.id, member.id)
    view = SolveView(guild.id, member.id)
    file = File(BytesIO(ch.image_bytes), filename="challenge.png")
    embed = Embed(
        title="Verification Challenge",
        description=f"Solve the challenge below. You have {ch.attempts_left} attempts.\nPress Solve to open the modal.",
        color=BLUE
    )
    embed.set_footer(text=f"Challenge expires in {CHALLENGE_TTL_MINUTES} minutes.")
    embed.set_image(url="attachment://challenge.png")
    await send_embed_interaction(interaction, embed, ephemeral=True, file=file, view=view)
    logger.info("Started verification challenge for user %s in guild %s", member.id, guild.id)

class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("Verification cog initialized")
        self.cleanup_expired_challenges.start()

    def cog_unload(self):
        self.cleanup_expired_challenges.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        if getattr(self.bot, "_verification_view_registered", False):
            return
        self.bot.add_view(PersistentVerificationView())
        self.bot._verification_view_registered = True
        logger.info("Persistent Verification view registered")

    @nextcord.slash_command(
        name="setupverification",
        description="Setup verification for this server",

        default_member_permissions=Permissions(administrator=True),
    )
    async def setupverification(
        self,
        interaction: Interaction,
        verifiedrole: nextcord.Role = SlashOption(
            name="verifiedrole",
            description="Role to grant when user verifies",
            required=True
        ),
        notverifiedrole: nextcord.Role = SlashOption(
            name="notverifiedrole",
            description="Role to assign to new members before verification",
            required=True
        ),
        channelofverification: nextcord.TextChannel = SlashOption(
            name="channelofverification",
            description="Channel where the Verify button will be posted",
            required=True,
            channel_types=[ChannelType.text]
        )
    ):
        if interaction.guild is None:
            embed = Embed(title="Server Only", description="Use this command inside a server.", color=RED)
            await send_embed_interaction(interaction, embed, ephemeral=True)
            return

        cfg = {
            "verified_role_id": verifiedrole.id,
            "not_verified_role_id": notverifiedrole.id,
            "channel_id": channelofverification.id
        }
        set_guild_config(interaction.guild.id, cfg)

        panel_embed = Embed(
            title="Server Verification",
            description="Press the button below to start verification.\nSolve the challenge to gain access.",
            color=GREEN
        )

        try:
            await channelofverification.send(embed=panel_embed, view=PanelViewWithEmoji())
            status_embed = Embed(
                title="Verification Setup Complete",
                description=(
                    f"Verification panel posted in {channelofverification.mention}\n"
                    f"Verified role: {verifiedrole.mention}\n"
                    f"Not verified role: {notverifiedrole.mention}"
                ),
                color=GREEN
            )
            await send_embed_interaction(interaction, status_embed, ephemeral=True)
            logger.info("setupverification by %s in guild %s", interaction.user.id, interaction.guild.id)
        except Exception as e:
            status_embed = Embed(
                title="Setup Saved, Posting Failed",
                description=f"Saved config, but failed to post in {channelofverification.mention}.\nError: {e}",
                color=RED
            )
            await send_embed_interaction(interaction, status_embed, ephemeral=True)
            logger.exception("Failed to post verification panel: %s", e)

    @nextcord.slash_command(
        name="refresh_emojis",
        description="Re-check and create application emojis from config. Only application emojis are created.",
        default_member_permissions=Permissions(administrator=True),
    )
    async def refresh_emojis(self, interaction: Interaction):
        from utils.emoji_manager import ensure_application_emojis, get_button_emoji
        try:
            await ensure_application_emojis(interaction.client)
            v = get_button_emoji("verify")
            s = get_button_emoji("solve")
            desc = []
            desc.append(f"Verify emoji: {'OK' if v else 'Not available'}")
            desc.append(f"Solve emoji: {'OK' if s else 'Not available'}")
            embed = Embed(title="Emoji Refresh", description="\n".join(desc), color=BLUE)
            await send_embed_interaction(interaction, embed, ephemeral=True)
        except Exception as e:
            embed = Embed(title="Emoji Refresh Failed", description=str(e), color=RED)
            await send_embed_interaction(interaction, embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: nextcord.Member):
        if member.bot:
            return

        cfg = get_guild_config(member.guild.id)
        if not cfg:
            return

        not_verified_role = member.guild.get_role(cfg["not_verified_role_id"])
        channel = member.guild.get_channel(cfg["channel_id"])

        if not_verified_role:
            try:
                await member.add_roles(not_verified_role, reason="New member verification pending")
            except Exception as e:
                logger.warning("Failed to assign not-verified role to user %s in guild %s: %s", member.id, member.guild.id, e)

        desc = "Welcome to the server! Please head to the verification channel to get verified."
        if channel:
            desc = f"Welcome to the server! Please go to {channel.mention} to get verified."

        embed = Embed(
            title="Welcome",
            description=desc,
            color=BLUE
        )
        try:
            await member.send(embed=embed)
        except Exception:
            logger.info("Couldn't DM user %s on join (DMs closed)", member.id)

    @tasks.loop(minutes=2)
    async def cleanup_expired_challenges(self):
        to_remove = []
        for (gid, uid), ch in list(challenges.items()):
            if ch.is_expired() or ch.attempts_left <= 0:
                to_remove.append((gid, uid))
        for k in to_remove:
            clear_challenge(*k)
        if to_remove:
            logger.info("Cleaned up %s expired challenges", len(to_remove))

    @cleanup_expired_challenges.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

def setup(bot: commands.Bot):
    bot.add_cog(Verification(bot))