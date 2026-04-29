"""Configuration manager for saving/loading plugin settings as JSON."""

import json
import os


class ConfigManager:
    """Manages plugin configuration save/load operations."""

    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), 'configs')
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)

    def save(self, config, filepath):
        """Save configuration dictionary to JSON file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True, f"Config saved: {filepath}"
        except Exception as e:
            return False, f"Error saving config: {str(e)}"

    def load(self, filepath):
        """Load configuration from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f), "Config loaded successfully"
        except Exception as e:
            return None, f"Error loading config: {str(e)}"

    def get_default_config(self):
        """Return default configuration."""
        return {
            "version": "001",
            "name_fields": {
                "field1": "",
                "field2": "",
                "separator": " - "
            },
            "description_fields": [],
            "polygon_style": {
                "border_color": "#FF0000",
                "border_width": 2,
                "fill_color": "#00FF00",
                "fill_opacity": 50
            },
            "conditional_colors": {
                "enabled": False,
                "field": "",
                "rules": []
            },
            "header": {
                "title": "Thông tin",
                "bg_color": "#1B5E20",
                "text_color": "#FFFFFF",
                "bold": True
            },
            "row_highlights": {
                "enabled": False,
                "rules": []
            }
        }
