import json
from pathlib import Path
from typing import Any, Dict, Optional

DATA_FILE = Path("data/role_messages.json")

def _ensure_file():
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps({"messages": {}}, indent=2))

def load_data() -> Dict[str, Any]:
    _ensure_file()
    try:
        return json.loads(DATA_FILE.read_text() or '{"messages": {}}')
    except json.JSONDecodeError:
        # Reset on corruption
        DATA_FILE.write_text(json.dumps({"messages": {}}, indent=2))
        return {"messages": {}}

def save_data(data: Dict[str, Any]) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2))

def set_message_mapping(
    message_id: int,
    guild_id: int,
    channel_id: int,
    mapping: Dict[str, int],
    created_by: int,
    title: Optional[str],
    description: str
) -> None:
    data = load_data()
    data["messages"][str(message_id)] = {
        "guild_id": guild_id,
        "channel_id": channel_id,
        "mappings": mapping,
        "created_by": created_by,
        "title": title,
        "description": description,
    }
    save_data(data)

def get_message_mapping(message_id: int) -> Optional[Dict[str, Any]]:
    data = load_data()
    return data["messages"].get(str(message_id))

def delete_message_mapping(message_id: int) -> None:
    data = load_data()
    if str(message_id) in data["messages"]:
        del data["messages"][str(message_id)]
        save_data(data)
