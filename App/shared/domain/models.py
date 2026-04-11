# shared/domain/models.py
from dataclasses import dataclass, field
from typing import List

@dataclass
class MedicalTerm:
    main_term: str
    synonyms: List[str] = field(default_factory=list)

@dataclass
class ProcessingResult:
    processed: int = 0
    errors: int = 0
