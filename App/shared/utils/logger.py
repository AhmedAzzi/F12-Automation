# shared/utils/logger.py
from typing import Callable, List

class AppLogger:
    """Centralized logging system that dispatches logs to registered callbacks."""
    def __init__(self):
        self._callbacks: List[Callable[[str, str], None]] = []
        
    def add_callback(self, callback: Callable[[str, str], None]):
        """Callback signature: def log_handler(message: str, level: str)"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            
    def remove_callback(self, callback: Callable[[str, str], None]):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def log(self, message: str, level: str = 'info'):
        """Levels: 'info', 'success', 'warning', 'error'"""
        for callback in self._callbacks:
            try:
                callback(message, level)
            except Exception as e:
                print(f"Error in logger callback: {e}")
        
        # Fallback to console if no callbacks registered
        if not self._callbacks:
            print(f"[{level.upper()}] {message}")

# Global logger instance
logger = AppLogger()
