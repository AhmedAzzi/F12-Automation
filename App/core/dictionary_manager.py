import json
from pathlib import Path

class DictionaryManager:
    def __init__(self, user_terms_file_path: Path, logger_callback=None):
        self.user_terms_file_path = user_terms_file_path
        self.logger = logger_callback or self._default_logger
        self.user_term_map = {}
        self.user_main_terms = set()
        self._load_user_terms()

    def _default_logger(self, message, level='info'):
        print(f"[{level.upper()}] {message}")

    def _load_user_terms(self):
        if not self.user_terms_file_path.exists():
            self.logger(f"Info: User medical terms file not found at {self.user_terms_file_path}. Creating an empty one.", 'info')
            self._save_user_terms_to_file([]) # Create an empty JSON array file
            return

        try:
            with open(self.user_terms_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.user_term_map = {}
            self.user_main_terms = set()

            for entry in data:
                main_term = entry.get("main_term")
                synonyms = entry.get("synonyms", [])
                
                if main_term:
                    self.user_main_terms.add(main_term.upper())
                    for term in synonyms:
                        self.user_term_map[term.upper()] = main_term.upper()
            self.logger(f"✓ Loaded {len(self.user_main_terms)} user-defined main terms and {len(self.user_term_map)} synonyms.", 'success')
        except json.JSONDecodeError:
            self.logger(f"Error: Could not decode JSON from {self.user_terms_file_path}. File might be corrupted.", 'error')
            self.user_term_map = {}
            self.user_main_terms = set()
        except Exception as e:
            self.logger(f"An unexpected error occurred while loading user terms: {e}", 'error')
            self.user_term_map = {}
            self.user_main_terms = set()

    def _save_user_terms_to_file(self, data):
        try:
            self.user_terms_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.user_terms_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger(f"✓ User-defined terms saved to {self.user_terms_file_path}", 'success')
        except Exception as e:
            self.logger(f"Error: Could not save user-defined terms to {self.user_terms_file_path}: {e}", 'error')

    def get_all_user_terms(self):
        """Returns the raw list of user terms as stored in the JSON file."""
        if not self.user_terms_file_path.exists():
            return []
        try:
            with open(self.user_terms_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.logger(f"Error: Could not decode JSON from {self.user_terms_file_path} when getting all terms.", 'error')
            return []
        except Exception as e:
            self.logger(f"An unexpected error occurred while getting all user terms: {e}", 'error')
            return []

    def add_term(self, main_term: str, synonyms: list):
        main_term_upper = main_term.upper()
        synonyms_upper = [s.upper() for s in synonyms]

        current_terms = self.get_all_user_terms()
        
        # Check if main_term already exists
        found = False
        for entry in current_terms:
            if entry.get("main_term", "").upper() == main_term_upper:
                # Update existing entry
                existing_synonyms = set(s.upper() for s in entry.get("synonyms", []))
                new_synonyms = list(existing_synonyms.union(synonyms_upper))
                entry["synonyms"] = new_synonyms
                found = True
                break
        
        if not found:
            # Add new entry
            current_terms.append({"main_term": main_term_upper, "synonyms": synonyms_upper})
        
        self._save_user_terms_to_file(current_terms)
        self._load_user_terms() # Reload internal map after saving
        self.logger(f"Added/Updated term: {main_term_upper} with synonyms {synonyms_upper}", 'info')

    def remove_term(self, main_term: str):
        main_term_upper = main_term.upper()
        current_terms = self.get_all_user_terms()
        
        updated_terms = [entry for entry in current_terms if entry.get("main_term", "").upper() != main_term_upper]
        
        if len(updated_terms) < len(current_terms):
            self._save_user_terms_to_file(updated_terms)
            self._load_user_terms() # Reload internal map after saving
            self.logger(f"Removed term: {main_term_upper}", 'info')
            return True
        self.logger(f"Term not found for removal: {main_term_upper}", 'warning')
        return False

    def get_term_map(self):
        return self.user_term_map

    def get_main_terms(self):
        return self.user_main_terms
