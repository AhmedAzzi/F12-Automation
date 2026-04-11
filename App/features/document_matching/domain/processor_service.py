# features/document_matching/domain/processor_service.py
import re
import shutil
import pythoncom
import win32com.client
from pathlib import Path

from shared.utils.logger import logger
from shared.domain.models import ProcessingResult
from shared.config.constants import SPECIAL_CASE_TWO_CR
from features.document_matching.domain.text_cleaner import TextCleaner
from features.document_matching.domain.matcher import ExamMatcher
from features.document_matching.infrastructure.document_reader import DocumentReader

class ProcessorService:
    """Core application service orchestrating document matching workflow."""
    
    def __init__(self, base_path: Path, temp_path: Path, dictionary_service):
        self.base_path = base_path
        self.temp_path = temp_path
        self.processed_folder = self.base_path / "Processed"
        
        term_map, main_terms = dictionary_service.get_all_terms()
        self.matcher = ExamMatcher(term_map, main_terms)

    def process(self) -> ProcessingResult:
        pythoncom.CoInitialize()
        word_app = None
        try:
            if not self.base_path.exists():
                raise FileNotFoundError(f"Base folder does not exist: {self.base_path}")

            self.temp_path.mkdir(parents=True, exist_ok=True)
            self.processed_folder.mkdir(exist_ok=True)

            logger.log("=" * 60)
            logger.log("🚀 Starting document processing...")
            logger.log(f"📁 Base folder: {self.base_path}")
            logger.log(f"📂 Temp folder: {self.temp_path}")
            logger.log("=" * 60)

            temp_files = [
                f for f in self.temp_path.iterdir()
                if f.is_file() and not f.name.startswith("~$")
                and f.suffix.lower() in [".doc", ".docx"]
            ]

            if not temp_files:
                logger.log("⚠️ No temp files found in temp folder", 'warning')
                return ProcessingResult(0, 0)

            base_files = [f for f in self.base_path.iterdir() if f.suffix.lower() in [".doc", ".docx"]]
            base_index = [(re.sub(r'\s+', ' ', f.stem.strip()).lower(), f) for f in base_files]
            logger.log(f"📊 Total base files indexed: {len(base_index)}\n")

            try:
                logger.log("📝 Initializing Microsoft Word...", 'info')
                word_app = win32com.client.DispatchEx("Word.Application")
                word_app.Visible = False
                word_app.DisplayAlerts = 0
                logger.log("✓ Word initialized successfully\n", 'success')
            except Exception as e:
                logger.log(f"❌ Failed to initialize Word: {e}", 'error')
                logger.log("⚠️ .doc files will be skipped", 'warning')

            doc_reader = DocumentReader(word_app)

            logger.log("=" * 60, 'info')
            logger.log("📖 Reading documents...", 'info')
            logger.log("=" * 60, 'info')

            processed = 0
            errors = 0

            for i, temp_file in enumerate(temp_files, 1):
                logger.log(f"\n🔄 [{i}/{len(temp_files)}] Reading: {temp_file.name}")
                if temp_file.suffix.lower() == ".doc" and not word_app:
                    logger.log(f"⚠️ Skipping .doc file (Word not available)", 'warning')
                    errors += 1
                    continue

                raw_first_line = doc_reader.get_first_line(temp_file)
                first_line = TextCleaner.clean_first_line(raw_first_line)
                
                if not first_line:
                    logger.log(f"⚠️ No readable text found in: {temp_file.name}", 'warning')
                    errors += 1
                    continue

                patient_name = TextCleaner.normalize_for_matching(first_line)
                logger.log(f"🔍 Looking for patient name: '{patient_name}'", 'info')

                matches = [f for name, f in base_index if name.startswith(patient_name)]
                
                if len(matches) == 1:
                    logger.log(f"✓ Found match: {matches[0].name}", 'success')
                    try:
                        dest_path = self.processed_folder / matches[0].name
                        shutil.copy(str(temp_file), str(dest_path))
                        logger.log(f"📂 Copied to: {dest_path.name}", 'success')
                        processed += 1
                    except Exception as e:
                        logger.log(f"❌ Failed to copy {temp_file.name} for single match: {e}", 'error')
                        errors += 1
                elif len(matches) > 1:
                    logger.log(f"⚠️ Multiple matches ({len(matches)}) for '{patient_name}' - comparing exam types...", 'warning')
                    for m in matches:
                        logger.log(f"   - {m.name}", 'info')
                    
                    temp_lines = doc_reader.get_first_n_lines(temp_file, 7)
                    if not temp_lines:
                        logger.log(f"❌ Could not read exam info from temp file", 'error')
                        errors += 1
                        continue
                    
                    logger.log(f"📄 Temp file content (first 7 lines):", 'info')
                    for line in temp_lines:
                        logger.log(f"   {line[:80]}...", 'info')
                    
                    best_match = None
                    best_similarity = 0.0
                    
                    for match_file in matches:
                        sim = self.matcher.calculate_similarity(temp_lines, match_file.stem)
                        if sim > best_similarity:
                            best_similarity = sim
                            best_match = match_file
                    
                    if best_match and best_similarity > 0.4:
                        logger.log(f"✓ Best match found: {best_match.name} (similarity: {best_similarity:.2%})", 'success')
                        try:
                            dest_path = self.processed_folder / best_match.name
                            shutil.copy(str(temp_file), str(dest_path))
                            logger.log(f"📂 Copied to: {dest_path.name}", 'success')
                            processed += 1
                        except Exception as e:
                            logger.log(f"❌ Failed to copy for best match: {e}", 'error')
                            errors += 1
                    else:
                        temp_text_full = ' '.join(doc_reader.get_first_n_lines(temp_file, 10)).lower()
                        if SPECIAL_CASE_TWO_CR in temp_text_full:
                            logger.log("🩷 Detected '2CR' marker — assigning to alternate base file.", "info")
                            forced_match = None
                            for m in matches:
                                if not (self.processed_folder / m.name).exists():
                                    forced_match = m
                                    break
                            
                            forced_match = forced_match or matches[0]
                            try:
                                dest_path = self.processed_folder / forced_match.name
                                shutil.copy(str(temp_file), str(dest_path))
                                logger.log(f"📄 Saved 2ᵉ Compte Rendu as: {dest_path.name}", "success")
                                processed += 1
                            except Exception as e:
                                logger.log(f"❌ Failed to save 2CR file: {e}", "error")
                                errors += 1
                        else:
                            logger.log(f"❌ No confident match found (best similarity: {best_similarity:.2%})", "error")
                            errors += 1
                else:
                    logger.log(f"⚠️ No match found for patient '{patient_name}'", 'error')
                    errors += 1

            logger.log("=" * 60)
            logger.log("✨ Processing complete!", 'success')
            logger.log(f"   ✅ Processed: {processed}", 'success')
            logger.log(f"   ❌ Errors: {errors}", 'error' if errors else 'info')
            logger.log("=" * 60)

            return ProcessingResult(processed, errors)

        finally:
            if word_app:
                try: word_app.Quit()
                except: pass
            pythoncom.CoUninitialize()
