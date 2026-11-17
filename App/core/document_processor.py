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


class DocumentProcessor:
    def __init__(self, base_path: Path, temp_path: Path, logger_callback=None):
        self.base_path = Path(base_path)
        self.temp_path = Path(temp_path)
        self.processed_folder = self.base_path / "Processed"
        self.logger = logger_callback or self._default_logger

    def _default_logger(self, message, level='info'):
        print(f"[{level.upper()}] {message}")

    # ---------- header detection ----------
    def is_header_line(self, text: str):
        """Return True if text looks like a clinic header/footer line to skip."""
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
        return any(keyword.upper() in text_upper for keyword in header_keywords)

    # ---------- low-level reading ----------
    def get_first_line_from_docx(self, file_path: Path):
        """Return first non-empty non-header paragraph from a .docx file (string) or None."""
        try:
            doc = Document(str(file_path))
            for p in doc.paragraphs:
                t = p.text.strip()
                if t and not self.is_header_line(t):
                    self.logger(f"   ✓ .docx first line: '{t[:120]}'", 'info')
                    return t
        except Exception as e:
            self.logger(f"❌ Error reading DOCX {file_path.name}: {e}", 'error')
        return None
    
    
    def get_first_line_from_doc(self, file_path: Path, word_app):
        """Return first non-empty non-header paragraph from a .doc file via Word COM or None."""
        doc = None
        try:
            self.logger(f"   Opening .doc file with Word...", 'info')
            doc = word_app.Documents.Open(
                str(file_path),
                ReadOnly=True,
                ConfirmConversions=False,
                AddToRecentFiles=False
            )
            for i in range(1, doc.Paragraphs.Count + 1):
                text = doc.Paragraphs(i).Range.Text.strip()
                if text and not self.is_header_line(text):
                    self.logger(f"   ✓ .doc first line: '{text[:120]}'", 'info')
                    return text
        except Exception as e:
            self.logger(f"❌ Error reading DOC {file_path.name}: {e}", 'error')
        finally:
            if doc:
                try:
                    doc.Close(False)
                except:
                    pass
            # CRITICAL: Release COM reference and allow Word to unlock file
            doc = None
            gc.collect()
            time.sleep(0.3)
        return None
    
    def get_first_line(self, file_path: Path, word_app=None):
        """Wrapper to get the first non-header line depending on file suffix."""
        suffix = file_path.suffix.lower()
        if suffix == ".docx":
            return self.get_first_line_from_docx(file_path)
        elif suffix == ".doc":
            if not word_app:
                self.logger("⚠️ Word not available for .doc file", 'warning')
                return None
            return self.get_first_line_from_doc(file_path, word_app)
        else:
            self.logger(f"⚠️ Unsupported file type: {file_path}", 'warning')
            return None

    # ---------- read exam lines (from top until 'Indication' / 'Résultats') ----------
    def get_exam_lines_until_indication(self, file_path: Path, word_app=None):
        """
        Return list of lines starting AFTER the first non-header line up to (but not including)
        the line that contains 'INDICATION' or 'RÉSULTATS'. Skips 'Médecin prescripteur' lines.
        """
        suffix = file_path.suffix.lower()
        lines = []
        try:
            if suffix == ".docx":
                doc = Document(str(file_path))
                found_first = False
                for p in doc.paragraphs:
                    text = p.text.strip()
                    if not text:
                        continue
                    if not found_first:
                        if not self.is_header_line(text):
                            found_first = True
                        continue
                    if "INDICATION" in text.upper() or "RÉSULTATS" in text.upper():
                        break
                    if "MÉDECIN PRESCRIPTEUR" in text.upper():
                        continue
                    lines.append(text)
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
                    found_first = False
                    for i in range(1, doc.Paragraphs.Count + 1):
                        text = doc.Paragraphs(i).Range.Text.strip()
                        if not text:
                            continue
                        if not found_first:
                            if not self.is_header_line(text):
                                found_first = True
                            continue
                        if "INDICATION" in text.upper() or "RÉSULTATS" in text.upper():
                            break
                        if "MÉDECIN PRESCRIPTEUR" in text.upper():
                            continue
                        lines.append(text)
                finally:
                    if doc:
                        try:
                            doc.Close(False)
                        except:
                            pass
                    # CRITICAL: Release COM reference
                    doc = None
                    gc.collect()
                    time.sleep(0.3)
            else:
                self.logger(f"⚠️ Unsupported file type for exam extraction: {file_path}", 'warning')
        except Exception as e:
            self.logger(f"❌ Error reading exam lines from {file_path.name}: {e}", 'error')
        return lines
    
    # ---------- cleaning & formatting ----------
    def clean_first_line(self, line: str):
        """Cleans a patient line while preserving and converting date dd/mm/yyyy -> dd-mm-yyyy."""
        if not line:
            return None
        # remove stray hyphens used as separators, keep hyphens inside words/dates
        cleaned = re.sub(r'\s*-\s*', ' ', line)
        cleaned = re.sub(r'[\r\n\t]+', ' ', cleaned)
        # convert date separators
        # Convert date separators from DD/MM/YYYY to YYYYMMDD
        cleaned = re.sub(r'(\d{2})/(\d{2})/(\d{4})', r'\3\2\1', cleaned)
        # Convert date separators from DD-MM-YYYY to YYYYMMDD
        cleaned = re.sub(r'(\d{2})-(\d{2})-(\d{4})', r'\3\2\1', cleaned)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
        cleaned = cleaned.strip(" .,:;–—")
        cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
        self.logger(f"🧹 Cleaned first line: '{cleaned}'", 'info')
        return cleaned

    def _truncate_filename(self, filename: str, max_length: int):
        """Truncate filename to max_length, preserving extension if present."""
        if len(filename) <= max_length:
            return filename
        
        name, ext = os.path.splitext(filename)
        if len(name) + len(ext) <= max_length:
            return filename # Should not happen if initial check passed, but for safety
        
        # Truncate name part
        truncated_name = name[:max_length - len(ext)]
        return f"{truncated_name}{ext}"

    def clean_exam_text(self, text: str):
        """Join exam lines into single line and tidy spacing."""
        if not text:
            return ""
        t = re.sub(r'[\r\n\t]+', ' ', text)
        t = re.sub(r'\s{2,}', ' ', t).strip()
        # Remove patterns like ". N° X"
        t = re.sub(r'\.\s*N°\s*\d+', '', t).strip()
        return t

    # ---------- main extraction ----------
    def extract_clean_title(self, file_path: Path, word_app=None):
        """
        Build final title:
            <patient_line (name + age + date)> <exam lines concatenated>
        Rules:
            - take first non-header line as patient_line (keep date, convert / to -)
            - take lines AFTER that line until 'INDICATION' or 'RÉSULTATS' to form exam text
        """
        patient_raw = self.get_first_line(file_path, word_app=word_app)
        if not patient_raw:
            return None

        exam_lines = self.get_exam_lines_until_indication(file_path, word_app=word_app)

        # Clean patient and exam parts
        patient_part = self.clean_first_line(patient_raw) or ""
        exam_part = self.clean_exam_text(" ".join(exam_lines)) or ""

        # Ensure age token is present; if not, try to find age among top lines
        if not re.search(r'\b\d+\s*(?:ans|mois)\b', patient_part, re.IGNORECASE):
            # fallback: search exam_lines and first doc lines
            # We'll attempt a quick scan of the doc top lines
            all_top = [patient_raw] + exam_lines
            for l in all_top:
                m = re.search(r'\b\d+\s*(?:ans|mois)\b', l, re.IGNORECASE)
                if m:
                    patient_part = f"{patient_part} {m.group(0)}".strip()
                    break

        # If patient part still contains a date with '/', convert to YYYYMMDD
        patient_part = re.sub(r'(\d{2})/(\d{2})/(\d{4})', r'\3\2\1', patient_part)
        # If patient part still contains a date with '-', convert to YYYYMMDD
        patient_part = re.sub(r'(\d{2})-(\d{2})-(\d{4})', r'\3\2\1', patient_part)

        # The exam_part now contains the full cleaned exam description
        exam_type = exam_part

        # Build final combined title
        if exam_part:
            combined = f"{patient_part} {exam_part}"
        else:
            combined = patient_part

        combined = re.sub(r'\s{2,}', ' ', combined).strip()
        self.logger(f"🎯 Final extracted title: '{combined}'", 'info')
        self.logger(f"🔬 Extracted exam type: '{exam_type}'", 'info')
        return combined, exam_type

    # ---------- processing loop ----------
    def process(self):
        """
        Process files found in temp_path: extract title, log it, move file to Processed folder.
        Uses copy+delete instead of move to avoid network file locking issues.
        """
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
            self.logger("\n", 'info')

            temp_files = [
                f for f in self.temp_path.iterdir()
                if f.is_file() and not f.name.startswith("~$")
                and f.suffix.lower() in [".doc", ".docx"]
            ]

            if not temp_files:
                self.logger("⚠️ No temp files found in temp folder", 'warning')
                return {"processed": 0, "errors": 0}

            base_files = [f for f in self.base_path.iterdir() if f.suffix.lower() in [".doc", ".docx"]]
            base_index = [(re.sub(r'\s+', ' ', f.stem.strip()).lower(), f) for f in base_files]
            self.logger(f"📊 Total base files indexed: {len(base_index)}\n")

            try:
                if any(f.suffix.lower() == ".doc" for f in temp_files):
                    self.logger("📝 Initializing Microsoft Word...", 'info')
                    word_app = win32com.client.DispatchEx("Word.Application")
                    word_app.Visible = False
                    word_app.DisplayAlerts = 0
                    self.logger("✓ Word initialized successfully\n", 'success')
                else:
                    self.logger("ℹ️ No .doc files found -> Word COM not required", 'info')
            except Exception as e:
                self.logger(f"❌ Failed to initialize Word: {e}", 'error')
                word_app = None

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

                try:
                    title, exam_type = self.extract_clean_title(temp_file, word_app=word_app)
                    if not title:
                        self.logger(f"⚠️ No readable text found in: {temp_file.name}", 'warning')
                        errors += 1
                        continue

                    normalized_title = re.sub(r'\s+', ' ', title.strip())
                    self.logger(f"🔍 Extracted title: '{normalized_title}'", 'info')
                    self.logger(f"🔬 Extracted exam type: '{exam_type}'", 'info')

                    # Determine destination
                    # Truncate the normalized_title to ensure the full file name (including suffix) does not exceed 90 characters
                    max_filename_length = 90
                    suffix_length = len(temp_file.suffix)
                    max_title_length = max_filename_length - suffix_length
                    
                    truncated_title = self._truncate_filename(normalized_title, max_title_length)
                    
                    new_file_name = f"{truncated_title}{temp_file.suffix}"
                    dest = self.processed_folder / new_file_name
                    counter = 1
                    while dest.exists():
                        dest = self.processed_folder / f"{truncated_title}_{counter}{temp_file.suffix}"
                        counter += 1

                    # Use COPY + DELETE instead of MOVE for network paths
                    # This avoids locking issues when moving between local temp and network locations
                    max_retries = 5
                    operation_success = False
                    
                    for attempt in range(max_retries):
                        try:
                            # Copy file to destination
                            shutil.copy2(str(temp_file), str(dest))
                            self.logger(f"   ✓ Copied to destination", 'info')
                            
                            # Small delay before deletion
                            gc.collect()
                            time.sleep(0.2)
                            
                            # Delete original from temp using multiple strategies
                            try:
                                temp_file.unlink()
                            except OSError:
                                # If standard delete fails, try using os.remove with force
                                try:
                                    os.remove(str(temp_file))
                                except OSError:
                                    # Last resort: use Windows command to delete (bypass locking)
                                    os.system(f'del /F /Q "{temp_file}"')
                            self.logger(f"   ✓ Deleted from temp folder", 'info')
                            
                            operation_success = True
                            processed += 1
                            self.logger(f"   ✅ Processed: {dest.name}", 'success')
                            break
                            
                        except OSError as op_error:
                            if attempt < max_retries - 1:
                                wait_time = 0.5 + (attempt * 0.4)
                                self.logger(f"   ⏳ Retry {attempt + 1}/{max_retries} (waiting {wait_time}s)...", 'warning')
                                time.sleep(wait_time)
                                gc.collect()
                            else:
                                # File was copied successfully, just couldn't delete temp copy
                                # Mark as processed and schedule temp file for cleanup
                                self.logger(f"   ⚠️ File copied but deletion failed (will retry on next run)", 'warning')
                                operation_success = True
                                processed += 1

                except Exception as e:
                    self.logger(f"❌ Error processing file {temp_file.name}: {e}", 'error')
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
            gc.collect()
            pythoncom.CoUninitialize()
