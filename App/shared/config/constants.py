# shared/config/constants.py

HEADER_KEYWORDS = [
    'CABINET', 'IMAGERIE', 'MÉDICALE', 'ERAHMA',
    'SCANNER', 'ÉCHOGRAPHIE', 'RADIOLOGIE', 'MAMMOGRAPHIE',
    'PANORAMIQUE DENTAIRE', 'NUMÉRISÉES',
    'Cité 200', 'palais des sports', 'Tigditt', 'Mostaganem',
    'Tél', '045 39 20 62', '0795 799 793',
    'cim.erahma', 'KAID SLIMANE',
    'SPECIALISTE en Radiologie', 'DIU en Imagerie'
]

# Words that mean the line should be skipped entirely
SKIP_KEYWORDS = [
    'MÉDECIN PRESCRIPTEUR'
]

# Word that means we should stop parsing lines
STOP_KEYWORDS = [
    'INDICATIONS'
]

# Special cases
SPECIAL_CASE_TWO_CR = "2cr"

# Regex patterns for normalization
REGEX_CLEAN_PATTERNS = [
    (r'\b\d+\s*(?:ans|mois)\b', ''),
    (r'\b\d+\s*(ans|an|mois|jour|jours)\b', ''),
    (r'\b(âge|age|ans|an|jours|mois)\b', ''),
    (r'\d{4}-\d{2}-\d{2}', ''),
    (r'\b(\d{2})/(\d{2})/(\d{4})\b', r'\3-\2-\1')
]

# Side indicators in medical exams that can be ignored for base matching
SIDE_INDICATORS = [
    'GAUCHE', 'DROIT', 'DROITE', 'BILATERAL', 'BILATERALE'
]
