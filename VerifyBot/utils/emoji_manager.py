import os
import json
import logging
from typing import Optional, Dict, Any

import aiohttp
import nextcord

logger = logging.getLogger(__name__)

CONFIG_DIR = "config"
GLOBAL_CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
os.makedirs(CONFIG_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "emoji_urls": {
        "verify": "https://cdn3.emoji.gg/emojis/2155-verify-green.gif",
        "solve": "https://cdn3.emoji.gg/emojis/3863_gearz.gif"
    },
    "application_emojis": {
        # "verify": {"id": "123", "name": "verify_green", "animated": true}
        # "solve": {"id": "456", "name": "solve_gear", "animated": true}
    }
}

def load_global_config() -> Dict[str, Any]:
    if not os.path.exists(GLOBAL_CONFIG_PATH):
        with open(GLOBAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        logger.info("Created global config at %s", GLOBAL_CONFIG_PATH)

    try:
        with open(GLOBAL_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Failed to load global config: %s", e)
        return DEFAULT_CONFIG.copy()

def save_global_config(cfg: Dict[str, Any]):
    try:
        with open(GLOBAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        logger.exception("Failed to write global config: %s", e)

async def _download_bytes(url: str) -> Optional[bytes]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.warning("Failed to download %s (status %s)", url, resp.status)
    except Exception as e:
        logger.exception("Error downloading %s: %s", url, e)
    return None

async def _create_application_emoji(bot: nextcord.Client, name: str, image_bytes: bytes) -> Optional[nextcord.PartialEmoji]:
    create_app_emoji = getattr(bot, "create_application_emoji", None)
    if create_app_emoji is None:
        raise RuntimeError("This nextcord version does not support bot.create_application_emoji(). Please upgrade nextcord.")

    emoji = await create_app_emoji(name=name, image=image_bytes)
    e_id = int(getattr(emoji, "id", 0) or (emoji.get("id") if isinstance(emoji, dict) else 0))
    e_name = getattr(emoji, "name", None) or (emoji.get("name") if isinstance(emoji, dict) else name)
    e_animated = bool(getattr(emoji, "animated", False) or (emoji.get("animated") if isinstance(emoji, dict) else False))
    logger.info("Created application emoji '%s' (%s)", e_name, e_id)
    return nextcord.PartialEmoji(name=e_name, id=e_id, animated=e_animated)

def _store_application_emoji(cfg: Dict[str, Any], name_key: str, pe: nextcord.PartialEmoji):
    cfg.setdefault("application_emojis", {})[name_key] = {
        "id": str(pe.id),
        "name": pe.name or name_key,
        "animated": bool(pe.animated),
    }
    save_global_config(cfg)

def get_application_emoji_partial(name_key: str) -> Optional[nextcord.PartialEmoji]:
    cfg = load_global_config()
    info = cfg.get("application_emojis", {}).get(name_key)
    if not info:
        return None
    try:
        return nextcord.PartialEmoji(name=info.get("name") or name_key, id=int(info["id"]), animated=bool(info.get("animated", False)))
    except Exception:
        return None

async def ensure_application_emojis(bot: nextcord.Client):
    """
    Ensure application emojis exist for keys in config emoji_urls.
    ONLY creates application emojis. No guild fallbacks.
    """
    cfg = load_global_config()
    urls = cfg.get("emoji_urls", {})

    for key, url in urls.items():
        if get_application_emoji_partial(key):
            continue

        image_bytes = await _download_bytes(url)
        if not image_bytes:
            logger.warning("Skipping app emoji '%s' due to download failure.", key)
            continue

        default_name = "verify_green" if key == "verify" else "solve_gear"
        pe = await _create_application_emoji(bot, default_name, image_bytes)
        if pe:
            _store_application_emoji(cfg, key, pe)

def get_button_emoji(key: str) -> Optional[nextcord.PartialEmoji]:
    """
    Returns the application-level PartialEmoji if available, otherwise None.
    """
    return get_application_emoji_partial(key)