# features/document_matching/domain/text_cleaner.py
import re
from shared.config.constants import REGEX_CLEAN_PATTERNS
from shared.utils.logger import logger

class TextCleaner:
    """Domain logic for normalizing text from documents."""
    
    @staticmethod
    def clean_first_line(line: str) -> str:
        if not line:
            return None
        cleaned = line.replace("-", "")
        cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
        
        for pattern, replacement in REGEX_CLEAN_PATTERNS:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
            
        cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
        logger.log(f"🧹 Cleaned first line: '{cleaned}'", 'info')
        return cleaned

    @staticmethod
    def normalize_for_matching(text: str) -> str:
        """Normalizes text for patient name matching by collapsing spaces and removing age units."""
        normalized = re.sub(r'\s+', ' ', text.strip()).lower()

        # Remove date, age, and unit words
        normalized = re.sub(r'\b\d+\s*(ans|an|mois|jour|jours)\b', '', normalized)
        normalized = re.sub(r'\b(âge|age|ans|an|jours|mois)\b', '', normalized)
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}', '', normalized)

        return re.sub(r'\s{2,}', ' ', normalized).strip()
