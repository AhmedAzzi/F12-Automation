# core/document_processor.py
import os
import shutil
import re
import time
import gc
from pathlib import Path
from difflib import SequenceMatcher
import json
from docx import Document
import win32com.client
import pythoncom
from core.dictionary_manager import DictionaryManager


class DocumentProcessor:
    def __init__(self, base_path: Path, temp_path: Path, logger_callback=None):
        self.base_path = Path(base_path)
        self.temp_path = Path(temp_path)
        self.processed_folder = self.base_path / "Processed"
        self.logger = logger_callback or self._default_logger
        # Construct synonyms_file_path relative to the application's root directory
        # This ensures it's always found correctly, regardless of the base_path passed to the constructor.
        app_root = Path(__file__).resolve().parents[1]
        self.unified_terms_file_path = app_root / "data" / "unified_medical_terms.json"
        self.user_terms_file_path = app_root / "data" / "user_medical_terms.json"
        
        self.dictionary_manager = DictionaryManager(self.user_terms_file_path, logger_callback=self.logger)
        self.term_map, self.all_main_terms = self._load_all_terms()

    def _default_logger(self, message, level='info'):
        print(f"[{level.upper()}] {message}")

    def _load_all_terms(self):
        # Load static terms
        static_term_map = {}
        static_main_terms = set()
        if not self.unified_terms_file_path.exists():
            self.logger(f"Error: Unified medical terms file not found at {self.unified_terms_file_path}", 'error')
        else:
            try:
                with open(self.unified_terms_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for entry in data:
                    main_term = entry.get("main_term")
                    synonyms = entry.get("synonyms", [])
                    if main_term:
                        static_main_terms.add(main_term.upper())
                        for term in synonyms:
                            static_term_map[term.upper()] = main_term.upper()
            except json.JSONDecodeError:
                self.logger(f"Error: Could not decode JSON from {self.unified_terms_file_path}", 'error')
            except Exception as e:
                self.logger(f"An unexpected error occurred while loading static terms: {e}", 'error')

        # Load user-defined terms
        user_term_map = self.dictionary_manager.get_term_map()
        user_main_terms = self.dictionary_manager.get_main_terms()

        # Merge terms (user-defined terms take precedence)
        combined_term_map = {**static_term_map, **user_term_map}
        combined_main_terms = static_main_terms.union(user_main_terms)

        return combined_term_map, combined_main_terms

    def get_first_line_from_docx(self, file_path: Path):
        try:
            doc = Document(str(file_path))
            for p in doc.paragraphs:
                if p.text.strip():
                    return p.text.strip()
        except Exception as e:
            self.logger(f"❌ Error reading DOCX {file_path.name}: {e}", 'error')
        return None

    def get_first_line_from_doc(self, file_path: Path, word_app):
        doc = None
        try:
            self.logger(f"   Opening .doc file with Word...", 'info')
            doc = word_app.Documents.Open(
                str(file_path),
                ReadOnly=True,
                ConfirmConversions=False,
                AddToRecentFiles=False
            )
            if doc.Paragraphs.Count > 0:
                text = doc.Paragraphs(1).Range.Text.strip()
                self.logger(f"   ✓ Read text from .doc: '{text[:50]}...'", 'info')
                return text
            else:
                self.logger(f"   ⚠️ No paragraphs found in .doc", 'warning')
                return None
        except Exception as e:
            self.logger(f"❌ Error reading DOC {file_path.name}: {e}", 'error')
            return None
        finally:
            if doc:
                try:
                    doc.Close(False)
                except:
                    pass

    def clean_first_line(self, line: str):
        if not line:
            return None
        cleaned = line.replace("-", "")
        cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
        cleaned = re.sub(r'\b\d+\s*(?:ans|mois)\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(\d{2})/(\d{2})/(\d{4})\b', r'\3-\2-\1', cleaned)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
        self.logger(f"🧹 Cleaned first line: '{cleaned}'", 'info')
        return cleaned

    def is_header_line(self, text: str):
        """Check if a line is part of the document header"""
        if not text:
            return True
        
        header_keywords = [
            'CABINET', 'IMAGERIE', 'MÉDICALE', 'ERAHMA',
            'SCANNER', 'ÉCHOGRAPHIE', 'RADIOLOGIE', 'MAMMOGRAPHIE',
            'PANORAMIQUE DENTAIRE', 'NUMÉRISÉES',
            'Cité 200', 'palais des sports', 'Tigditt', 'Mostaganem',
            'Tél', '045 39 20 62', '0795 799 793',
            'cim.erahma', 'KAID SLIMANE',
            'SPECIALISTE en Radiologie', 'DIU en Imagerie'
        ]
        
        text_upper = text.upper()
        # If line contains any header keyword, it's part of header
        for keyword in header_keywords:
            if keyword.upper() in text_upper:
                return True
        
        return False

    def get_first_n_lines(self, file_path: Path, n: int, word_app=None):
        """Get first N non-empty lines from document, skipping header"""
        suffix = file_path.suffix.lower()
        lines = []
        
        try:
            if suffix == ".docx":
                doc = Document(str(file_path))
                for p in doc.paragraphs:
                    text = p.text.strip()
                    if "INDICATIONS" in text.upper():
                        break # Stop reading if "Indications" is found
                    if "MÉDECIN PRESCRIPTEUR" in text.upper(): # Skip lines containing "Médecin prescripteur"
                        continue
                    # Skip empty lines and header lines
                    if text and not self.is_header_line(text):
                        lines.append(text)
                        if len(lines) >= n:
                            break
            elif suffix == ".doc":
                if not word_app:
                    return []
                doc = None
                try:
                    doc = word_app.Documents.Open(
                        str(file_path),
                        ReadOnly=True,
                        ConfirmConversions=False,
                        AddToRecentFiles=False
                    )
                    for i in range(1, doc.Paragraphs.Count + 1):
                        text = doc.Paragraphs(i).Range.Text.strip()
                        if "INDICATIONS" in text.upper():
                            break # Stop reading if "Indications" is found
                        if "MÉDECIN PRESCRIPTEUR" in text.upper(): # Skip lines containing "Médecin prescripteur"
                            continue
                        # Skip empty lines and header lines
                        if text and not self.is_header_line(text):
                            lines.append(text)
                            if len(lines) >= n:
                                break
                finally:
                    if doc:
                        try:
                            doc.Close(False)
                        except:
                            pass
        except Exception as e:
            self.logger(f"❌ Error reading lines from {file_path.name}: {e}", 'error')
        
        return lines

    def extract_exam_type(self, text: str):
        """Extract exam type from text with contextual detection"""
        if not text:
            return ''

        text_upper = text.upper()
        found_terms = set()

        # Check for direct matches with main terms
        for main_term in self.all_main_terms:
            if main_term in text_upper:
                found_terms.add(main_term)
        
        # Check for matches with synonyms and map to main term
        for synonym, main_term in self.term_map.items():
            if synonym in text_upper:
                found_terms.add(main_term)

        return ' '.join(sorted(list(found_terms))).strip()



    def normalize_medical_terms(self, text: str) -> str:
        """Normalize common medical exam synonyms for consistent comparison using loaded synonyms."""
        normalized = text.upper()

        # Sort replacements by key length in descending order to avoid partial replacements
        # e.g., "RX MAMMOGRAPHIE UNILATERALE" should be replaced before "MAMMOGRAPHIE"
        sorted_replacements = sorted(self.term_map.items(), key=lambda item: len(item[0]), reverse=True)

        for old, new in sorted_replacements:
            normalized = normalized.replace(old, new)

        # Remove optional side indicators after synonym replacement
        normalized = re.sub(r'\b(GAUCHE|DROIT|DROITE|BILATERAL(E)?)\b', '', normalized)

        normalized = re.sub(r'\s{2,}', ' ', normalized).strip()
        return normalized


    def match_exam_type(self, temp_lines: list, base_filename: str):
        """Compare exam types between temp file content and base filename"""
        # Extract exam info from temp file lines
        temp_text = ' '.join(temp_lines)
        temp_exam = self.extract_exam_type(temp_text)
        
        # Extract exam info from filename
        base_exam = self.extract_exam_type(base_filename)
        
        if not temp_exam or not base_exam:
            return 0.0

        # ✅ Apply medical synonym normalization
        temp_exam = self.normalize_medical_terms(temp_exam)
        base_exam = self.normalize_medical_terms(base_exam)

        # ✅ Simplify by removing side indicators (optional)
        temp_exam = re.sub(r'\b(GAUCHE|DROIT|DROITE|BILATERAL(E)?)\b', '', temp_exam)
        base_exam = re.sub(r'\b(GAUCHE|DROIT|DROITE|BILATERAL(E)?)\b', '', base_exam)
        
        # Calculate similarity
        similarity = SequenceMatcher(None, temp_exam, base_exam).ratio()
        self.logger(f"   📋 Temp exam: '{temp_exam}'", 'info')
        self.logger(f"   📋 Base exam: '{base_exam}'", 'info')
        self.logger(f"   📊 Similarity: {similarity:.2%}", 'info')
        
        return similarity

    def get_first_line(self, file_path: Path, word_app=None):
        suffix = file_path.suffix.lower()
        if suffix == ".docx":
            raw = self.get_first_line_from_docx(file_path)
        elif suffix == ".doc":
            if not word_app:
                self.logger(f"⚠️ Word instance not available for .doc file", 'warning')
                return None
            raw = self.get_first_line_from_doc(file_path, word_app)
        else:
            self.logger(f"⚠️ Unsupported file type: {file_path}", 'warning')
            return None

        return self.clean_first_line(raw)


    

    def process(self):
        pythoncom.CoInitialize()
        word_app = None
        try:
            if not self.base_path.exists():
                raise FileNotFoundError(f"Base folder does not exist: {self.base_path}")

            self.temp_path.mkdir(parents=True, exist_ok=True)
            self.processed_folder.mkdir(exist_ok=True)

            self.logger("=" * 60)
            self.logger("🚀 Starting document processing...")
            self.logger(f"📁 Base folder: {self.base_path}")
            self.logger(f"📂 Temp folder: {self.temp_path}")
            self.logger("=" * 60)

            # Display loaded unified terms for verification
            self.logger("\n--- Loaded Unified Medical Terms ---", 'info')
            self.logger(f"  Total main terms: {len(self.all_main_terms)}", 'debug')
            self.logger(f"  Total synonyms mapped: {len(self.term_map)}", 'debug')
            self.logger("\n", 'info')

            temp_files = [
                f for f in self.temp_path.iterdir()
                if f.is_file() and not f.name.startswith("~$")
                and f.suffix.lower() in [".doc", ".docx"]
                #     and (f.name.lower().endswith("_temp.doc") or f.name.lower().endswith("_temp.docx"))

            ]

            if not temp_files:
                self.logger("⚠️ No temp files found in temp folder", 'warning')
                return {"processed": 0, "errors": 0}

            base_files = [f for f in self.base_path.iterdir() if f.suffix.lower() in [".doc", ".docx"]]
            base_index = [(re.sub(r'\s+', ' ', f.stem.strip()).lower(), f) for f in base_files]
            self.logger(f"📊 Total base files indexed: {len(base_index)}\n")

            # Initialize Word
            try:
                self.logger("📝 Initializing Microsoft Word...", 'info')
                word_app = win32com.client.DispatchEx("Word.Application")
                word_app.Visible = False
                word_app.DisplayAlerts = 0
                self.logger("✓ Word initialized successfully\n", 'success')
            except Exception as e:
                self.logger(f"❌ Failed to initialize Word: {e}", 'error')
                self.logger("⚠️ .doc files will be skipped", 'warning')

            # Read & Match
            self.logger("=" * 60, 'info')
            self.logger("📖 Reading documents...", 'info')
            self.logger("=" * 60, 'info')

            processed = 0
            errors = 0

            for i, temp_file in enumerate(temp_files, 1):
                self.logger(f"\n🔄 [{i}/{len(temp_files)}] Reading: {temp_file.name}")
                if temp_file.suffix.lower() == ".doc" and not word_app:
                    self.logger(f"⚠️ Skipping .doc file (Word not available)", 'warning')
                    errors += 1
                    continue

                first_line = self.get_first_line(temp_file, word_app)
                if not first_line:
                    self.logger(f"⚠️ No readable text found in: {temp_file.name}", 'warning')
                    errors += 1
                    continue

                normalized = re.sub(r'\s+', ' ', first_line.strip()).lower()

                # Remove date, age, and unit words like "ans", "mois", "jours"
                normalized = re.sub(r'\b\d+\s*(ans|an|mois|jour|jours)\b', '', normalized)
                normalized = re.sub(r'\b(âge|age|ans|an|jours|mois)\b', '', normalized)
                normalized = re.sub(r'\d{4}-\d{2}-\d{2}', '', normalized)

                # Collapse spaces again
                normalized = re.sub(r'\s{2,}', ' ', normalized).strip()

                patient_name = normalized

                self.logger(f"🔍 Looking for patient name: '{patient_name}'", 'info')

                matches = [f for name, f in base_index if name.startswith(patient_name.lower())]
                if len(matches) == 1:
                    self.logger(f"✓ Found match: {matches[0].name}", 'success')
                    try:
                        dest_path = self.processed_folder / matches[0].name
                        shutil.copy(str(temp_file), str(dest_path))
                        self.logger(f"📂 Copied to: {dest_path.name}", 'success')
                        processed += 1
                    except Exception as e:
                        self.logger(f"❌ Failed to copy {temp_file.name} for single match: {e}", 'error')
                        errors += 1
                elif len(matches) > 1:
                    self.logger(f"⚠️ Multiple matches ({len(matches)}) for '{patient_name}' - comparing exam types...", 'warning')
                    for m in matches:
                        self.logger(f"   - {m.name}", 'info')
                    
                    # Get first 7 lines from temp file (after header) to capture exam info
                    temp_lines = self.get_first_n_lines(temp_file, 7, word_app)
                    if not temp_lines:
                        self.logger(f"❌ Could not read exam info from temp file", 'error')
                        errors += 1
                        continue
                    
                    self.logger(f"📄 Temp file content (first 7 lines):", 'info')
                    for line in temp_lines:
                        self.logger(f"   {line[:80]}...", 'info')
                    
                    # Find best match based on exam type
                    best_match = None
                    best_similarity = 0.0
                    
                    for match_file in matches:
                        similarity = self.match_exam_type(temp_lines, match_file.stem)
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_match = match_file
                    
                    # Only accept if similarity is above threshold (40% - lowered for better matching)
                    if best_match and best_similarity > 0.4:
                        self.logger(f"✓ Best match found: {best_match.name} (similarity: {best_similarity:.2%})", 'success')
                        try:
                            dest_path = self.processed_folder / best_match.name
                            shutil.copy(str(temp_file), str(dest_path))
                            self.logger(f"📂 Copied to: {dest_path.name}", 'success')
                            processed += 1
                        except Exception as e:
                            self.logger(f"❌ Failed to copy {temp_file.name} for best match: {e}", 'error')
                            errors += 1
                    else:
                        # 🩷 Check for '2CR' special case (second compte rendu)
                        temp_text_full = ' '.join(self.get_first_n_lines(temp_file, 10, word_app)).lower()
                        if "2cr" in temp_text_full:
                            self.logger("🩷 Detected '2CR' marker — assigning to alternate base file.", "info")

                            # Try to find the base file among matches that hasn’t been used yet
                            forced_match = None
                            for m in matches:
                                dest_path = self.processed_folder / m.name
                                if not dest_path.exists():  # not already copied
                                    forced_match = m
                                    break

                            forced_match = forced_match or matches[0]  # fallback to first match

                            try:
                                dest_path = self.processed_folder / forced_match.name
                                shutil.copy(str(temp_file), str(dest_path))
                                self.logger(f"📄 Saved 2ᵉ Compte Rendu as: {dest_path.name}", "success")
                                processed += 1
                                continue  # skip error count
                            except Exception as e:
                                self.logger(f"❌ Failed to save 2CR file: {e}", "error")
                                errors += 1
                                continue
                        else:
                            self.logger(f"❌ No confident match found (best similarity: {best_similarity:.2%})", "error")
                            errors += 1

                else:
                    self.logger(f"⚠️ No match found for patient '{patient_name}'", 'error')
                    errors += 1

            self.logger("=" * 60)
            self.logger("✨ Processing complete!", 'success')
            self.logger(f"   ✅ Processed: {processed}", 'success')
            self.logger(f"   ❌ Errors: {errors}", 'error' if errors else 'info')
            self.logger("=" * 60)

            return {"processed": processed, "errors": errors}

        finally:
            if word_app:
                try:
                    word_app.Quit()
                except:
                    pass
            pythoncom.CoUninitialize()
