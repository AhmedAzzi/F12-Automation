# features/document_matching/infrastructure/document_reader.py
from pathlib import Path
from typing import List, Optional
from docx import Document
import win32com.client

from shared.utils.logger import logger
from shared.config.constants import HEADER_KEYWORDS, STOP_KEYWORDS, SKIP_KEYWORDS

class DocumentReader:
    """Infrastructure service to read Word documents."""
    
    def __init__(self, word_app=None):
        self.word_app = word_app

    def is_header_line(self, text: str) -> bool:
        """Check if a line is part of the document header"""
        if not text:
            return True
        text_upper = text.upper()
        for keyword in HEADER_KEYWORDS:
            if keyword.upper() in text_upper:
                return True
        return False

    def get_first_line(self, file_path: Path) -> Optional[str]:
        suffix = file_path.suffix.lower()
        if suffix == ".docx":
            return self._get_first_line_docx(file_path)
        elif suffix == ".doc":
            return self._get_first_line_doc(file_path)
        else:
            logger.log(f"⚠️ Unsupported file type: {file_path}", 'warning')
            return None

    def _get_first_line_docx(self, file_path: Path) -> Optional[str]:
        try:
            doc = Document(str(file_path))
            for p in doc.paragraphs:
                if p.text.strip():
                    return p.text.strip()
        except Exception as e:
            logger.log(f"❌ Error reading DOCX {file_path.name}: {e}", 'error')
        return None

    def _get_first_line_doc(self, file_path: Path) -> Optional[str]:
        if not self.word_app:
            logger.log(f"⚠️ Word instance not available for .doc file {file_path.name}", 'warning')
            return None
        doc = None
        try:
            logger.log(f"   Opening .doc file with Word...", 'info')
            doc = self.word_app.Documents.Open(
                str(file_path), ReadOnly=True, ConfirmConversions=False, AddToRecentFiles=False
            )
            if doc.Paragraphs.Count > 0:
                text = doc.Paragraphs(1).Range.Text.strip()
                logger.log(f"   ✓ Read text from .doc: '{text[:50]}...'", 'info')
                return text
            else:
                logger.log(f"   ⚠️ No paragraphs found in .doc", 'warning')
                return None
        except Exception as e:
            logger.log(f"❌ Error reading DOC {file_path.name}: {e}", 'error')
            return None
        finally:
            if doc:
                try: doc.Close(False)
                except: pass

    def get_first_n_lines(self, file_path: Path, n: int) -> List[str]:
        """Get first N non-empty lines from document, skipping header"""
        suffix = file_path.suffix.lower()
        lines = []
        try:
            if suffix == ".docx":
                doc = Document(str(file_path))
                for p in doc.paragraphs:
                    text = p.text.strip()
                    if any(k in text.upper() for k in STOP_KEYWORDS): break
                    if any(k in text.upper() for k in SKIP_KEYWORDS): continue
                    if text and not self.is_header_line(text):
                        lines.append(text)
                        if len(lines) >= n: break
            elif suffix == ".doc":
                if not self.word_app: return []
                doc = None
                try:
                    doc = self.word_app.Documents.Open(
                        str(file_path), ReadOnly=True, ConfirmConversions=False, AddToRecentFiles=False
                    )
                    for i in range(1, doc.Paragraphs.Count + 1):
                        text = doc.Paragraphs(i).Range.Text.strip()
                        if any(k in text.upper() for k in STOP_KEYWORDS): break
                        if any(k in text.upper() for k in SKIP_KEYWORDS): continue
                        if text and not self.is_header_line(text):
                            lines.append(text)
                            if len(lines) >= n: break
                finally:
                    if doc:
                        try: doc.Close(False)
                        except: pass
        except Exception as e:
            logger.log(f"❌ Error reading lines from {file_path.name}: {e}", 'error')
        return lines
