import json
import os

CONFIG_PATH = "app_config.json"

def get_app_config():
    if not os.path.exists(CONFIG_PATH):
        return {"notifications_enabled": True}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {"notifications_enabled": True}

def save_app_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
