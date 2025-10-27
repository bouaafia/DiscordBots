import json
import os
import logging

logger = logging.getLogger(__name__)

DATA_DIR = "data"
CONFIG_PATH = os.path.join(DATA_DIR, "guild_configs.json")
os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f)
        logger.info("Created guild config store at %s", CONFIG_PATH)

def _load_all():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Failed to read guild config store: %s", e)
        return {}

def _save_all(obj):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
    except Exception as e:
        logger.exception("Failed to write guild config store: %s", e)

def get_guild_config(guild_id: int):
    return _load_all().get(str(guild_id))

def set_guild_config(guild_id: int, config: dict):
    allc = _load_all()
    allc[str(guild_id)] = config
    _save_all(allc)
    logger.info("Saved verification config for guild %s", guild_id)

def delete_guild_config(guild_id: int):
    allc = _load_all()
    allc.pop(str(guild_id), None)
    _save_all(allc)
    logger.info("Deleted verification config for guild %s", guild_id)

def list_guild_ids():
    return list(_load_all().keys())