# features/dictionary/domain/dictionary_service.py
from pathlib import Path
from typing import Dict, Set, Tuple, List

from shared.utils.logger import logger
from shared.domain.models import MedicalTerm
from features.dictionary.infrastructure.json_terms_repository import JsonTermsRepository

class DictionaryService:
    """Application service managing business logic for terms and dictionaries."""
    
    def __init__(self, unified_path: Path, user_path: Path):
        self.unified_repo = JsonTermsRepository(unified_path)
        self.user_repo = JsonTermsRepository(user_path)
        
        self.user_term_map: Dict[str, str] = {}
        self.user_main_terms: Set[str] = set()
        
        # Load initially
        self._load_user_terms()

    def _load_user_terms(self):
        data = self.user_repo.load_terms()
        self.user_term_map.clear()
        self.user_main_terms.clear()

        for entry in data:
            main_term = entry.get("main_term")
            synonyms = entry.get("synonyms", [])
            
            if main_term:
                self.user_main_terms.add(main_term.upper())
                for term in synonyms:
                    self.user_term_map[term.upper()] = main_term.upper()
        
        if self.user_main_terms:
            logger.log(f"✓ Loaded {len(self.user_main_terms)} user-defined main terms.", 'success')

    def get_all_terms(self) -> Tuple[Dict[str, str], Set[str]]:
        """Returns merged unified and user terms. User terms take precedence."""
        static_term_map = {}
        static_main_terms = set()
        
        unified_data = self.unified_repo.load_terms()
        if not unified_data:
            logger.log("Warning: Unified medical terms loaded empty.", 'warning')
            
        for entry in unified_data:
            main_term = entry.get("main_term")
            synonyms = entry.get("synonyms", [])
            if main_term:
                static_main_terms.add(main_term.upper())
                for term in synonyms:
                    static_term_map[term.upper()] = main_term.upper()

        # Merge (user overrides static)
        combined_term_map = {**static_term_map, **self.user_term_map}
        combined_main_terms = static_main_terms.union(self.user_main_terms)

        return combined_term_map, combined_main_terms

    def get_user_terms_raw(self) -> List[dict]:
        return self.user_repo.load_terms()

    def add_user_term(self, main_term: str, synonyms: List[str]):
        main_term_upper = main_term.upper()
        synonyms_upper = [s.upper() for s in synonyms]

        current_terms = self.get_user_terms_raw()
        
        found = False
        for entry in current_terms:
            if entry.get("main_term", "").upper() == main_term_upper:
                existing_synonyms = set(s.upper() for s in entry.get("synonyms", []))
                entry["synonyms"] = list(existing_synonyms.union(synonyms_upper))
                found = True
                break
        
        if not found:
            current_terms.append({"main_term": main_term_upper, "synonyms": synonyms_upper})
        
        if self.user_repo.save_terms(current_terms):
            self._load_user_terms()
            logger.log(f"Added/Updated term: {main_term_upper} with synonyms {synonyms_upper}", 'info')
            return True
        return False

    def remove_user_term(self, main_term: str) -> bool:
        main_term_upper = main_term.upper()
        current_terms = self.get_user_terms_raw()
        
        updated_terms = [entry for entry in current_terms if entry.get("main_term", "").upper() != main_term_upper]
        
        if len(updated_terms) < len(current_terms):
            if self.user_repo.save_terms(updated_terms):
                self._load_user_terms()
                logger.log(f"Removed term: {main_term_upper}", 'info')
                return True
        
        logger.log(f"Term not found for removal: {main_term_upper}", 'warning')
        return False
