# features/word_automation/logic/word_app_manager.py
import pythoncom
import win32com.client
import gc
import time
import subprocess

from shared.utils.logger import logger

class WordAppManager:
    """Manages Microsoft Word instances (COM objects)."""
    
    def close_all_instances(self):
        pythoncom.CoInitialize()
        try:
            logger.log("📝 Attempting to close all Word instances...", 'info')
            closed_docs = 0

            try:
                word_app = win32com.client.GetActiveObject("Word.Application")
                doc_count = word_app.Documents.Count
                logger.log(f"   Found {doc_count} open document(s)", 'info')

                while word_app.Documents.Count > 0:
                    doc_name = word_app.Documents(1).Name
                    word_app.Documents(1).Close(False)
                    logger.log(f"   ✓ Closed: {doc_name}", 'success')
                    closed_docs += 1

                word_app.Quit()
                logger.log("   ✓ Word application closed", 'success')

                gc.collect()
                time.sleep(1)
                logger.log("✅ Word cleanup completed via COM", 'success')
                return {"closed": closed_docs, "error": None}

            except Exception as e:
                # Fallback implementation
                logger.log("   💀 Attempting process-level Word shutdown (taskkill)...", 'info')
                try:
                    result = subprocess.run(
                        ["taskkill", "/f", "/im", "WINWORD.EXE"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        logger.log("   ✓ All Word processes terminated successfully", 'success')
                        return {"closed": 0, "error": None}
                    else:
                        logger.log(f"   ⚠️ taskkill output: {result.stderr.strip()}", 'warning')
                        return {"closed": 0, "error": result.stderr.strip()}
                except Exception as e2:
                    logger.log(f"   ❌ Failed to force-close Word: {e2}", 'error')
                    return {"closed": 0, "error": str(e2)}

        except Exception as e:
            logger.log(f"❌ Fatal error closing Word: {e}", 'error')
            return {"closed": 0, "error": str(e)}
        finally:
            pythoncom.CoUninitialize()
