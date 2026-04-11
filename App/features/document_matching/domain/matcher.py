# features/document_matching/domain/matcher.py
import re
from difflib import SequenceMatcher
from typing import Dict, Set

from shared.utils.logger import logger
from shared.config.constants import SIDE_INDICATORS

class ExamMatcher:
    """Domain logic for extracting and matching exam types."""
    
    def __init__(self, term_map: Dict[str, str], all_main_terms: Set[str]):
        self.term_map = term_map
        self.all_main_terms = all_main_terms

    def extract_exam_type(self, text: str) -> str:
        """Extract exam type from text with contextual detection"""
        if not text:
            return ''
        text_upper = text.upper()
        found_terms = set()

        for main_term in self.all_main_terms:
            if main_term in text_upper:
                found_terms.add(main_term)
        
        for synonym, main_term in self.term_map.items():
            if synonym in text_upper:
                found_terms.add(main_term)

        return ' '.join(sorted(list(found_terms))).strip()

    def normalize_medical_terms(self, text: str) -> str:
        """Normalize common medical exam synonyms for consistent comparison."""
        normalized = text.upper()
        sorted_replacements = sorted(self.term_map.items(), key=lambda item: len(item[0]), reverse=True)

        for old, new in sorted_replacements:
            normalized = normalized.replace(old, new)

        for side in SIDE_INDICATORS:
            normalized = re.sub(rf'\b{side}\b', '', normalized)

        return re.sub(r'\s{2,}', ' ', normalized).strip()

    def calculate_similarity(self, temp_lines: list, base_filename: str) -> float:
        """Compare exam types between temp file content and base filename"""
        temp_text = ' '.join(temp_lines)
        temp_exam = self.extract_exam_type(temp_text)
        base_exam = self.extract_exam_type(base_filename)
        
        if not temp_exam or not base_exam:
            return 0.0

        temp_exam = self.normalize_medical_terms(temp_exam)
        base_exam = self.normalize_medical_terms(base_exam)

        for side in SIDE_INDICATORS:
            temp_exam = re.sub(rf'\b{side}\b', '', temp_exam)
            base_exam = re.sub(rf'\b{side}\b', '', base_exam)
        
        similarity = SequenceMatcher(None, temp_exam, base_exam).ratio()
        logger.log(f"   📋 Temp exam: '{temp_exam}'", 'info')
        logger.log(f"   📋 Base exam: '{base_exam}'", 'info')
        logger.log(f"   📊 Similarity: {similarity:.2%}", 'info')
        
        return similarity
