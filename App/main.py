# main.py
import tkinter as tk
from pathlib import Path
from shared.config.settings import AppSettings
from presentation.main_window import MainWindow

def main():
    root = tk.Tk()
    
    app_root = Path(__file__).resolve().parent
    settings = AppSettings(app_root)
    
    app = MainWindow(root, settings)
    root.mainloop()

if __name__ == "__main__":
    main()