# features/word_automation/logic/temp_cleaner_service.py
import pythoncom
from pathlib import Path

from shared.utils.logger import logger

class TempCleanerService:
    """Service to clean temporary files."""
    
    def clean_temp_folder(self, temp_path: Path):
        pythoncom.CoInitialize()
        try:
            logger.log("=" * 60, 'info')
            logger.log("🧹 Starting temp folder cleanup...", 'info')
            logger.log("=" * 60, 'info')

            if not temp_path.exists():
                logger.log(f"   ⚠️ Temp folder does not exist: {temp_path}", 'warning')
                return {"deleted": 0, "skipped": 0, "errors": 0, "error": "Folder does not exist"}

            deleted_count = 0
            skipped_count = 0
            error_count = 0

            for file in temp_path.iterdir():
                if file.is_file():
                    try:
                        file.unlink()
                        logger.log(f"   ✓ Deleted: {file.name}", 'success')
                        deleted_count += 1
                    except PermissionError as e:
                        msg = str(e).lower()
                        if "used by another process" in msg or "processus" in msg or "winerror 32" in msg:
                            logger.log(f"   ⏭️ Skipped (in use): {file.name}", 'info')
                            skipped_count += 1
                        else:
                            logger.log(f"   ⚠️ Permission issue deleting {file.name}: {e}", 'warning')
                            error_count += 1
                    except Exception as e:
                        logger.log(f"   ❌ Failed to delete {file.name}: {e}", 'error')
                        error_count += 1

            logger.log("\n" + "=" * 60, 'info')
            logger.log("✨ Cleanup complete!", 'success')
            logger.log(f"   ✅ Deleted: {deleted_count} file(s)", 'success')
            if skipped_count > 0:
                logger.log(f"   ⏭️ Skipped (in use): {skipped_count} file(s)", 'info')
            if error_count > 0:
                logger.log(f"   ❌ Errors: {error_count}", 'error')
            logger.log("=" * 60, 'info')

            return {"deleted": deleted_count, "skipped": skipped_count, "errors": error_count, "error": None}

        except Exception as e:
            logger.log(f"\n❌ CRITICAL ERROR during cleanup: {e}", 'error')
            return {"deleted": 0, "skipped": 0, "errors": 0, "error": str(e)}
        finally:
            pythoncom.CoUninitialize()
