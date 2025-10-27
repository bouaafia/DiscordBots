from __future__ import annotations

import re
from typing import Dict, Tuple, Optional, List

import nextcord
from nextcord.ext import commands

from utils import embeds
from utils.storage import set_message_mapping

TEMPLATES: Dict[str, Dict[str, object]] = {
    "minimal": {
        "label": "Minimal",
        "title": "Choose Your Roles",
        "description": (
            "React to get roles. Add or remove your reaction at any time to toggle the role.\n\n"
            "Notes:\n"
            "• These roles may unlock channels or pings.\n"
            "• You can choose multiple roles.\n"
            "• If something doesn't work, ping an admin."
        ),
        "example_pairs": [
            ("🔔", "Updates"),
            ("🎉", "Events"),
            ("📢", "Announcements"),
        ],
    },
    "notifications": {
        "label": "Notifications",
        "title": "Pick Your Notifications",
        "description": (
            "Choose which announcements you want to be pinged for by reacting below.\n\n"
            "• Events: Get notified about events and streams.\n"
            "• Updates: Get news, patch notes, and changelogs.\n"
            "• Giveaways: Get pinged for giveaways and contests.\n\n"
            "Remove a reaction to stop getting those pings."
        ),
        "example_pairs": [
            ("🎟️", "Giveaways"),
            ("🛠️", "Updates"),
            ("📅", "Events"),
        ],
    },
    "games": {
        "label": "Game Roles",
        "title": "Select Your Game Roles",
        "description": (
            "React for the games you play to find teammates and unlock LFG channels.\n\n"
            "• Choose as many as you like.\n"
            "• Remove a reaction to leave the role.\n"
            "• New games are added regularly—ask staff if something is missing!"
        ),
        "example_pairs": [
            ("🎮", "FPS"),
            ("⚔️", "RPG"),
            ("🏁", "Racing"),
        ],
    },
    "pronouns": {
        "label": "Pronoun Roles",
        "title": "Choose Your Pronouns",
        "description": (
            "Pick pronoun roles so others know how to address you. You may choose multiple.\n\n"
            "• React to add a role.\n"
            "• Remove the reaction to remove the role.\n"
            "• If you prefer a pronoun not listed, contact a moderator."
        ),
        "example_pairs": [
            ("💬", "He/Him"),
            ("💖", "She/Her"),
            ("💜", "They/Them"),
        ],
    },
}


CUSTOM_WITH_ID = re.compile(r"^<a?:(?P<name>\w+):(?P<id>\d{15,25})>$")
CUSTOM_NAME_ONLY = re.compile(r"^<a?:(?P<name>\w+):>$")
COLON_NAME = re.compile(r"^:(?P<name>\w+):$")

def parse_emoji_role_lines(text: str) -> Tuple[Dict[str, int], list[str]]:
    """
    Parses lines of 'left:right' where right is a role_id and left can be:
      - <:name:id> / <a:name:id>
      - <:name:> / <a:name:>
      - :name:
      - emoji_id (digits)
      - Unicode emoji (one emoji glyph or sequence)
    Returns:
      mappings: dict where keys are one of:
        - 'e:<id>' for custom emoji by ID
        - 'u:<emoji>' for unicode emoji
        - 'n:<name>' for custom emoji name to resolve later
      values are role_ids (int)
      errors: list of human-friendly error messages
    """
    mappings: Dict[str, int] = {}
    errors: list[str] = []

    if not text.strip():
        errors.append("No emoji:role pairs provided.")
        return mappings, errors

    lines = [ln for ln in text.splitlines() if ln.strip()]
    for idx, raw in enumerate(lines, start=1):
        left, sep, right = raw.rpartition(":")
        if not sep:
            errors.append(f"Line {idx}: Missing ':' separator. Expected something like '<:name:id>:role_id' or '😀:role_id'.")
            continue
        left = left.strip()
        role_id_str = right.strip()
        if not role_id_str.isdigit():
            errors.append(f"Line {idx}: Role id '{role_id_str}' must be numeric.")
            continue
        role_id = int(role_id_str)

        key: Optional[str] = None

        m = CUSTOM_WITH_ID.match(left)
        if m:
            key = f"e:{int(m.group('id'))}"
        else:
            m2 = CUSTOM_NAME_ONLY.match(left)
            if m2:
                name = m2.group("name")
                key = f"n:{name}"
            else:
                m3 = COLON_NAME.match(left)
                if m3:
                    name = m3.group("name")
                    key = f"n:{name}"
                else:
                    if left.isdigit():
                        key = f"e:{int(left)}"
                    else:
                        if re.search(r"[A-Za-z_]", left):
                            key = f"n:{left}"
                        else:
                            key = f"u:{left}"

        if key is None:
            errors.append(f"Line {idx}: Could not parse '{raw}'.")
            continue

        if key in mappings:
            errors.append(f"Line {idx}: Duplicate emoji mapping for '{raw}'.")
            continue

        mappings[key] = role_id

    return mappings, errors

def resolve_channel_from_text(guild: nextcord.Guild, raw: str) -> Optional[nextcord.TextChannel]:
    s = raw.strip()
    m = re.match(r"^<#(\d{15,25})>$", s)
    if m:
        ch = guild.get_channel(int(m.group(1)))
        return ch if isinstance(ch, nextcord.TextChannel) else None
    if re.match(r"^\d{15,25}$", s):
        ch = guild.get_channel(int(s))
        return ch if isinstance(ch, nextcord.TextChannel) else None
    return None

def build_template_preview_embed(template_key: str) -> nextcord.Embed:
    template = TEMPLATES.get(template_key, TEMPLATES["minimal"])
    title = template["title"] 
    description = template["description"]  
    example_pairs: List[tuple[str, str]] = template.get("example_pairs", []) 

    preview = embeds.base(str(title), str(description))
    if example_pairs:
        lines = [f"• {em} → @{role}" for em, role in example_pairs]
        legend = "\n".join(lines)
        preview.add_field(name="React with", value=legend[:1024], inline=False)

    preview.add_field(
        name="How it works",
        value="React to add a role. Remove your reaction to remove the role.",
        inline=False
    )
    return preview

async def format_custom_emoji_str(guild: nextcord.Guild, emoji_id: int) -> str:
    emoji_obj = await guild.fetch_emoji(emoji_id)
    if emoji_obj:
        prefix = "a" if emoji_obj.animated else ""
        return f"<{prefix}:{emoji_obj.name}:{emoji_obj.id}>"
    return f"<:emoji:{emoji_id}>"

async def build_role_legend_fields(
    guild: nextcord.Guild,
    resolved_mappings: Dict[str, int]
) -> List[tuple[str, str]]:
    """
    Returns a list of (field_name, field_value) tuples chunked to fit embed limits.
    """
    lines: List[str] = []

    for key, role_id in resolved_mappings.items():
        role = guild.get_role(role_id)
        if not role:
            continue

        if key.startswith("e:"):
            emoji_id = int(key.split(":", 1)[1])
            emoji_str = await format_custom_emoji_str(guild, emoji_id)
        else:
            emoji_str = key.split(":", 1)[1]

        lines.append(f"• {emoji_str} → {role.mention}")

    fields: List[tuple[str, str]] = []
    if not lines:
        return fields

    chunk: List[str] = []
    current_len = 0
    for ln in lines:
        if current_len + len(ln) + 1 > 1024 and chunk:
            fields.append(("React with", "\n".join(chunk)))
            chunk = [ln]
            current_len = len(ln) + 1
        else:
            chunk.append(ln)
            current_len += len(ln) + 1
    if chunk:
        fields.append(("React with", "\n".join(chunk)))

    return fields

class RoleMessageModal(nextcord.ui.Modal):
    def __init__(self, bot: commands.Bot, template_key: str = "minimal"):
        super().__init__(title="Build Reaction Roles Message")
        self.bot = bot
        self.template_key = template_key if template_key in TEMPLATES else "minimal"
        template = TEMPLATES[self.template_key]

        self.title_input = nextcord.ui.TextInput(
            label="Title (optional)",
            style=nextcord.TextInputStyle.short,
            required=False,
            max_length=200,
            placeholder="Leave blank to use template title"
        )
        self.description_input = nextcord.ui.TextInput(
            label="Message Body (optional)",
            style=nextcord.TextInputStyle.paragraph,
            required=False,
            max_length=4000,
            placeholder="Leave blank to use template message"
        )
        self.pairs_input = nextcord.ui.TextInput(
            label="Emoji ↔ Role Pairs (one per line)",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            placeholder="e.g., <:name:id>:role • 😀:role • :name::role • emoji_id:role"
        )
        self.channel_input = nextcord.ui.TextInput(
            label="Target Channel (ID or mention)",
            style=nextcord.TextInputStyle.short,
            required=True,
            placeholder="<#123456789012345678> or 123456789012345678"
        )


        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.pairs_input)
        self.add_item(self.channel_input)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        assert interaction.guild is not None

        raw_mappings, errs = parse_emoji_role_lines(str(self.pairs_input.value))

        resolved_mappings: Dict[str, int] = {}
        name_conflicts: list[str] = []
        if interaction.guild and raw_mappings:
            guild_emojis = list(interaction.guild.emojis)
            lower_index: Dict[str, list[nextcord.Emoji]] = {}
            exact_index: Dict[str, list[nextcord.Emoji]] = {}
            for e in guild_emojis:
                exact_index.setdefault(e.name, []).append(e)
                lower_index.setdefault(e.name.lower(), []).append(e)

            for key, role_id in raw_mappings.items():
                if key.startswith("n:"):
                    name = key[2:]

                    exact_matches = exact_index.get(name, [])
                    candidate: Optional[nextcord.Emoji] = None

                    if len(exact_matches) == 1:
                        candidate = exact_matches[0]
                    else:
                        ci_matches = lower_index.get(name.lower(), [])
                        if len(ci_matches) == 1:
                            candidate = ci_matches[0]

                    if candidate is None:
                        if not exact_matches and not lower_index.get(name.lower(), []):
                            errs.append(f"Emoji named '{name}' not found in this server. Use <:name:id> or emoji ID.")
                        else:
                            examples = exact_matches or lower_index.get(name.lower(), [])
                            ids_preview = ", ".join(str(e.id) for e in examples[:5])
                            more = " ..." if len(examples) > 5 else ""
                            name_conflicts.append(f"'{name}' matches {len(examples)} emojis. Specify ID. Example IDs: {ids_preview}{more}")
                        continue

                    new_key = f"e:{candidate.id}"
                    if new_key in resolved_mappings or (new_key in raw_mappings and new_key != key):
                        errs.append(f"Duplicate mapping for emoji '{name}' (ID {candidate.id}).")
                        continue
                    resolved_mappings[new_key] = role_id
                else:
                    if key in resolved_mappings:
                        errs.append(f"Duplicate mapping for emoji key '{key}'.")
                        continue
                    resolved_mappings[key] = role_id

        errs.extend(name_conflicts)

        channel = resolve_channel_from_text(interaction.guild, str(self.channel_input.value))
        if channel is None:
            errs.append("Invalid channel. Use a channel mention like #channel or the numeric channel ID.")

        if interaction.guild and resolved_mappings:
            for _, role_id in list(resolved_mappings.items()):
                role = interaction.guild.get_role(role_id)
                if role is None:
                    errs.append(f"Role not found for ID {role_id}.")
                else:
                    me = interaction.guild.me
                    if not me.guild_permissions.manage_roles:
                        errs.append("Bot lacks 'Manage Roles' permission.")
                        break
                    if role >= me.top_role:
                        errs.append(f"Bot's top role must be higher than {role.name} ({role.id}).")

        if errs:
            await interaction.response.send_message(
                embed=embeds.error("Setup Validation Failed", "\n".join(f"• {e}" for e in errs)),
                ephemeral=True
            )
            return

        template = TEMPLATES.get(self.template_key, TEMPLATES["minimal"])
        title = (str(self.title_input.value).strip() or str(template["title"])).strip()
        description = (str(self.description_input.value).strip() or str(template["description"])).strip()

        preview = embeds.base(title or "Reaction Roles", description)

        fields = await build_role_legend_fields(interaction.guild, resolved_mappings)
        if fields:
            for fname, fval in fields:
                preview.add_field(name=fname, value=fval, inline=False)

        preview.add_field(
            name="How it works",
            value="• React to add a role\n• Remove your reaction to remove the role\n• You may pick multiple roles",
            inline=False
        )

        try:
            sent = await channel.send(embed=preview)
        except Exception as e:
            await interaction.response.send_message(
                embed=embeds.error("Failed to Send Message", f"Could not send the embed in {channel.mention}.\nError: {e}"),
                ephemeral=True
            )
            return

        add_errors = []
        for key in resolved_mappings.keys():
            try:
                if key.startswith("e:"):
                    emoji_id = int(key.split(":", 1)[1])
                    emoji_obj = self.bot.get_emoji(emoji_id) or nextcord.PartialEmoji(name="emoji", id=emoji_id, animated=False)
                    await sent.add_reaction(emoji_obj)
                else:
                    uni = key.split(":", 1)[1]
                    await sent.add_reaction(uni)
            except Exception as e:
                add_errors.append(f"Failed to add reaction for {key}: {e}")

        set_message_mapping(
            message_id=sent.id,
            guild_id=sent.guild.id,
            channel_id=sent.channel.id,
            mapping=resolved_mappings,
            created_by=interaction.user.id,
            title=title,
            description=description
        )

        success_desc = (
            f"Template used: {TEMPLATES[self.template_key]['label']}\n"
            f"Reaction roles message created in {channel.mention}.\n[Jump to message]({sent.jump_url})"
        )
        if add_errors:
            success_desc += "\n\nSome reactions could not be added:\n" + "\n".join(f"• {err}" for err in add_errors)

        await interaction.response.send_message(
            embed=embeds.success("Setup Complete", success_desc),
            ephemeral=True
        )

class TemplateSelect(nextcord.ui.Select):
    def __init__(self, parent_view: "SetupView"):
        self.parent_view = parent_view
        options = [
            nextcord.SelectOption(
                label=TEMPLATES[k]["label"],  # type: ignore
                value=k,
                description=f"Preview and use the {TEMPLATES[k]['label']} template"  # type: ignore
            )
            for k in TEMPLATES.keys()
        ]
        super().__init__(placeholder="Select a template (preview shown immediately)", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        self.parent_view.template_key = self.values[0]
        # Show an aesthetic preview embed (ephemeral) so admins see how it will look
        preview = build_template_preview_embed(self.parent_view.template_key)
        await interaction.response.send_message(embed=preview, ephemeral=True)

class SetupView(nextcord.ui.View):
    def __init__(self, bot: commands.Bot, timeout: Optional[float] = 600):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.template_key: str = "minimal"
        self.add_item(TemplateSelect(self))

    @nextcord.ui.button(label="Open Builder", style=nextcord.ButtonStyle.blurple, emoji="⚙️")
    async def open_builder(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(RoleMessageModal(self.bot, template_key=self.template_key))

class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @nextcord.slash_command(
        name="setup",
        description="Create a reaction roles message via an interactive builder.",
        default_member_permissions=nextcord.Permissions(administrator=True)
    )
    async def setup_cmd(self, interaction: nextcord.Interaction):
        assert interaction.guild is not None

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=embeds.error("Permission Denied", "You must be a server administrator to use /setup."),
                ephemeral=True
            )
            return

        guide = embeds.info(
            "Reaction Roles Setup",
            (
                "Pick a template to preview how the message will look, then click 'Open Builder'. "
                "If you leave Title or Message blank in the modal, the template will be used.\n\n"
                "Emoji ↔ Role format (one per line):\n"
                "• <:name:id>:role_id or emoji_id:role_id\n"
                "• 😀:role_id (Unicode)\n"
                "• :name::role_id or <:name:>:role_id (name-only; resolved in this server)\n\n"
                "Tip: Ensure the bot's top role is above the roles you want it to assign."
            )
        )
        view = SetupView(self.bot)
        await interaction.response.send_message(embed=guide, view=view, ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(SetupCog(bot))
