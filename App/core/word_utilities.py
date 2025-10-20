# core/word_utilities.py
import pythoncom
import win32com.client
import gc
import time
from pathlib import Path


class WordUtilities:
    """Utility class for managing Word instances and file operations"""
    
    def __init__(self, logger_callback=None):
        self.logger = logger_callback or self._default_logger
    
    def _default_logger(self, message, level='info'):
        print(f"[{level.upper()}] {message}")

    def close_all_word_instances(self):
        """Close all open Microsoft Word instances (via COM or process fallback)."""
        pythoncom.CoInitialize()
        try:
            self.logger("📝 Attempting to close all Word instances...", 'info')
            closed_docs = 0

            try:
                # Try to connect to a running Word instance via COM
                word_app = win32com.client.GetActiveObject("Word.Application")
                doc_count = word_app.Documents.Count
                self.logger(f"   Found {doc_count} open document(s)", 'info')

                # Close all documents without saving
                while word_app.Documents.Count > 0:
                    doc_name = word_app.Documents(1).Name
                    word_app.Documents(1).Close(False)
                    self.logger(f"   ✓ Closed: {doc_name}", 'success')
                    closed_docs += 1

                # Quit Word gracefully
                word_app.Quit()
                self.logger("   ✓ Word application closed", 'success')

                gc.collect()
                time.sleep(1)
                self.logger("✅ Word cleanup completed via COM", 'success')
                return {"closed": closed_docs, "error": None}

            except Exception as e:
                error_msg = str(e).lower()
                known_codes = [-2147221021]
                known_phrases = [
                    "operation unavailable", 
                    "opération non disponible", 
                    "no object", 
                    "aucun objet"
                ]

                if getattr(e, "hresult", None) in known_codes or any(p in error_msg for p in known_phrases):
                    self.logger("   ⚠️ Word not visible to COM (possibly different user/session)", 'warning')
                else:
                    self.logger(f"   ⚠️ Unexpected COM error: {e}", 'warning')

                # ------------------------------------------------------------------
                # 🪓 Fallback: kill any WINWORD.EXE process directly
                # ------------------------------------------------------------------
                import subprocess
                try:
                    self.logger("   💀 Attempting process-level Word shutdown (taskkill)...", 'info')
                    result = subprocess.run(
                        ["taskkill", "/f", "/im", "WINWORD.EXE"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        self.logger("   ✓ All Word processes terminated successfully", 'success')
                        return {"closed": 0, "error": None}
                    else:
                        self.logger(f"   ⚠️ taskkill output: {result.stderr.strip()}", 'warning')
                        return {"closed": 0, "error": result.stderr.strip()}
                except Exception as e2:
                    self.logger(f"   ❌ Failed to force-close Word: {e2}", 'error')
                    return {"closed": 0, "error": str(e2)}

        except Exception as e:
            self.logger(f"❌ Fatal error closing Word: {e}", 'error')
            return {"closed": 0, "error": str(e)}
        finally:
            pythoncom.CoUninitialize()

    def clean_temp_folder(self, temp_path: Path):
        """
        Clean all files from temp folder.
        
        Args:
            temp_path: Path to the temp folder

        Returns:
            dict: {"deleted": count, "skipped": count, "errors": count, "error": error_msg}
        """
        pythoncom.CoInitialize()
        try:
            self.logger("=" * 60, 'info')
            self.logger("🧹 Starting temp folder cleanup...", 'info')
            self.logger("=" * 60, 'info')

            # Step 1: Delete temp files
            self.logger("\n🗑️ Deleting temp files...", 'info')

            if not temp_path.exists():
                self.logger(f"   ⚠️ Temp folder does not exist: {temp_path}", 'warning')
                return {"deleted": 0, "skipped": 0, "errors": 0, "error": "Folder does not exist"}

            deleted_count = 0
            skipped_count = 0
            error_count = 0

            for file in temp_path.iterdir():
                if file.is_file():
                    try:
                        file.unlink()
                        self.logger(f"   ✓ Deleted: {file.name}", 'success')
                        deleted_count += 1
                    except PermissionError as e:
                        # File currently in use — just skip, not an error
                        msg = str(e).lower()
                        if "used by another process" in msg or "processus" in msg or "winerror 32" in msg:
                            self.logger(f"   ⏭️ Skipped (in use): {file.name}", 'info')
                            skipped_count += 1
                        else:
                            self.logger(f"   ⚠️ Permission issue deleting {file.name}: {e}", 'warning')
                            error_count += 1
                    except Exception as e:
                        self.logger(f"   ❌ Failed to delete {file.name}: {e}", 'error')
                        error_count += 1

            self.logger("\n" + "=" * 60, 'info')
            self.logger("✨ Cleanup complete!", 'success')
            self.logger(f"   ✅ Deleted: {deleted_count} file(s)", 'success')
            if skipped_count > 0:
                self.logger(f"   ⏭️ Skipped (in use): {skipped_count} file(s)", 'info')
            if error_count > 0:
                self.logger(f"   ❌ Errors: {error_count}", 'error')
            self.logger("=" * 60, 'info')

            return {"deleted": deleted_count, "skipped": skipped_count, "errors": error_count, "error": None}

        except Exception as e:
            self.logger(f"\n❌ CRITICAL ERROR during cleanup: {e}", 'error')
            import traceback
            self.logger(traceback.format_exc(), 'error')
            return {"deleted": 0, "skipped": 0, "errors": 0, "error": str(e)}

        finally:
            pythoncom.CoUninitialize()
