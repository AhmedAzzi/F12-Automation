# features/dictionary/infrastructure/json_terms_repository.py
import json
from pathlib import Path
from typing import List, Dict, Any

from shared.utils.logger import logger

class JsonTermsRepository:
    """Handles low-level read/write operations for JSON dictionary files."""
    def __init__(self, file_path: Path):
        self.file_path = file_path

    def load_terms(self) -> List[Dict[str, Any]]:
        """Loads terms from JSON file. Returns an empty list if file doesn't exist."""
        if not self.file_path.exists():
            return []
            
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.log(f"Error: Could not decode JSON from {self.file_path}. File might be corrupted.", 'error')
            return []
        except Exception as e:
            logger.log(f"An unexpected error occurred while loading {self.file_path}: {e}", 'error')
            return []

    def save_terms(self, terms_data: List[Dict[str, Any]]) -> bool:
        """Saves terms to JSON file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(terms_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.log(f"Error: Could not save terms to {self.file_path}: {e}", 'error')
            return False
