# shared/config/settings.py
import json
from pathlib import Path

class AppSettings:
    """Manages application-level settings loaded from config.json."""
    
    def __init__(self, app_root: Path):
        self.app_root = app_root
        self.config_file = app_root / "config.json"
        
        self.user_medical_terms_path = app_root / "data" / "user_medical_terms.json"
        self.unified_medical_terms_path = app_root / "data" / "unified_medical_terms.json"
        self.icons_dir = app_root / "icons"
        
        self._load_config()

    def _load_config(self):
        if not self.config_file.exists():
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Allow config.json to override paths
            if "user_medical_terms_path" in data and data["user_medical_terms_path"]:
                self.user_medical_terms_path = Path(data["user_medical_terms_path"])
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_setting(self, key: str, value: str):
        data = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
            except:
                pass
                
        data[key] = value
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
