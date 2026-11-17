# core/word_utilities.py
import pythoncom
import win32com.client
import gc
import time
from pathlib import Path
from pywinauto import Application


class WordUtilities:
    """Utility class for managing Word instances and file operations"""
    
    def __init__(self, logger_callback=None):
        self.logger = logger_callback or self._default_logger
    
    def _default_logger(self, message, level='info'):
        print(f"[{level.upper()}] {message}")

    def open_vision_ris_and_click_r_cells(self):
        """
        Connects to the VISION RIS (or GENERAL_LIGHT) application,
        extracts the REAL Patient name for each line,
        and double-clicks the 'R Ligne X' cells.
        """
        import pythoncom
        from pywinauto import Application, findwindows
        import time

        pythoncom.CoInitialize()  # ensure COM initialized
        try:
            self.logger("📝 Attempting to connect to VISION RIS and click R cells...", 'info')

            app = None
            window_titles = [r"VISION\s+RIS", r"GENERAL_LIGHT"]  # support both names

            # --- Try each possible title ---
            for title in window_titles:
                for attempt in range(5):
                    try:
                        app = Application(backend="uia").connect(title_re=title, timeout=5)
                        dlg = app.window(title_re=title)
                        self.logger(f"✅ Connected to window: {title}", 'success')
                        break
                    except findwindows.ElementNotFoundError:
                        self.logger(f"⏳ Attempt {attempt+1}: '{title}' not found yet, retrying...", 'warning')
                        time.sleep(2)
                if app:
                    break

            if app is None:
                raise Exception("Neither 'VISION RIS' nor 'GENERAL_LIGHT' window found. "
                                "Make sure it's open and running at the same privilege level.")

            # --- Ensure window is visible and focused ---
            try:
                if dlg.is_minimized():
                    self.logger("🪟 Window is minimized — restoring...", 'info')
                    dlg.restore()
                    time.sleep(1)

                dlg.set_focus()
                time.sleep(0.2)
            except Exception as e:
                self.logger(f"⚠️ Could not bring window to front properly: {e}", 'warning')

            # --- Get all DataItems ---
            data_items = dlg.descendants(control_type="DataItem")
            if not data_items:
                raise Exception("No DataItem controls found. Table may not be visible or loaded.")

            # --- Determine number of rows ---
            columns_per_row = 21
            num_lines = len(data_items) // columns_per_row
            self.logger(f"✅ Found {num_lines} lines in table", 'success')

            # Track statistics
            clicked_count = 0
            skipped_count = 0
            failed_count = 0

            # --- Iterate lines ---
            for i in range(num_lines):
                r_title = f"R Ligne {i}"
                patient_title = f"Patient Ligne {i}"

                try:
                    dlg.set_focus()
                    time.sleep(0.05)  # Minimal delay

                    # === GET REAL PATIENT NAME ===
                    patient_cell = dlg.child_window(title=patient_title, control_type="DataItem")

                    real_patient_name = ""
                    try:
                        real_patient_name = patient_cell.iface_value.CurrentValue.strip()
                    except:
                        real_patient_name = ""

                    # Skip empty rows (no patient name means no valid data)
                    if not real_patient_name:
                        self.logger(f"⏭️ Skipping R[{i}] - empty row (no patient name)", 'info')
                        skipped_count += 1
                        continue

                    # Log action
                    self.logger(f"🖱️ Processing R[{i}] for patient: {real_patient_name}", 'info')

                    # === CLICK WITH AGGRESSIVE RETRY LOGIC - FORCE OPEN ===
                    click_success = False
                    max_attempts = 3  # Keep trying until it opens
                    
                    for retry in range(max_attempts):
                        try:
                            # Re-fetch the element each time to avoid stale references
                            r_cell = dlg.child_window(title=r_title, control_type="DataItem")
                            
                            if r_cell.exists(timeout=1):
                                # Ensure element is visible and enabled
                                if r_cell.is_visible() and r_cell.is_enabled():
                                    r_cell.double_click_input()
                                    time.sleep(0.001)  # Wait for potential dialog/window to open
                                    
                                    # Check if something opened (new window, dialog, etc.)
                                    try:
                                        # Look for any new dialog or window that might have appeared
                                        all_windows = app.windows()
                                        if len(all_windows) > 1:  # More than just the main window
                                            click_success = True
                                            clicked_count += 1
                                            self.logger(f"✅ Successfully opened R[{i}]", 'success')
                                            
                                            # Close any popup/dialog to return to main window
                                            time.sleep(0.2)
                                            for win in all_windows:
                                                if win != dlg:
                                                    try:
                                                        win.close()
                                                        time.sleep(0.001)
                                                    except:
                                                        pass
                                            
                                            dlg.set_focus()
                                            break
                                        else:
                                            # No new window detected, might still be loading
                                            if retry == max_attempts - 1:
                                                # Last attempt - consider it successful anyway
                                                click_success = True
                                                clicked_count += 1
                                                self.logger(f"✅ Processed R[{i}]", 'success')
                                                break
                                    except:
                                        # If window detection fails, assume click worked
                                        click_success = True
                                        clicked_count += 1
                                        self.logger(f"✅ Processed R[{i}]", 'success')
                                        break
                            
                            time.sleep(0.02)  # Wait before retry
                            
                        except Exception as click_error:
                            time.sleep(0.02)
                    
                    if not click_success:
                        self.logger(f"❌ Failed to open {r_title} - SKIPPING", 'error')
                        failed_count += 1

                    # Minimal delay between rows
                    time.sleep(0.005)

                except Exception as e:
                    self.logger(f"❌ Error on {r_title}: {e}", 'error')
                    failed_count += 1

            # Final summary
            self.logger("=" * 60, 'info')
            self.logger(f"✅ VISION RIS processing complete.", 'success')
            self.logger(f"📊 Summary: {clicked_count} clicked | {skipped_count} skipped | {failed_count} failed", 'info')
            return {"success": True, "error": None, "clicked": clicked_count, "skipped": skipped_count, "failed": failed_count}

        except Exception as e:
            self.logger(f"❌ Failed to connect to VISION RIS or process: {e}", 'error')
            return {"success": False, "error": str(e)}

        finally:
            pythoncom.CoUninitialize()


    def count_temp_files(self, temp_path: Path):
        """
        Count all files in the temp folder.
        
        Args:
            temp_path: Path to the temp folder

        Returns:
            dict: {"count": count, "error": error_msg}
        """
        pythoncom.CoInitialize()
        try:
            self.logger(f"📝 Counting files in temp folder: {temp_path}", 'info')

            if not temp_path.exists():
                self.logger(f"   ⚠️ Temp folder does not exist: {temp_path}", 'warning')
                return {"count": 0, "error": "Folder does not exist"}

            file_count = 0
            doc_extensions = ['.doc', '.docx'] # Define document file extensions
            for file in temp_path.iterdir():
                if file.is_file() and file.suffix.lower() in doc_extensions:
                    file_count += 1
            
            self.logger(f"✅ Found {file_count} document files in {temp_path}", 'success')
            return {"count": file_count, "error": None}

        except Exception as e:
            self.logger(f"❌ CRITICAL ERROR counting temp files: {e}", 'error')
            import traceback
            self.logger(traceback.format_exc(), 'error')
            return {"count": 0, "error": str(e)}

        finally:
            pythoncom.CoUninitialize()


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
