# presentation/main_window.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import tempfile
from PIL import Image, ImageTk

from shared.config.settings import AppSettings
from shared.config.theme import THEMES
from shared.utils.logger import logger

from features.dictionary.domain.dictionary_service import DictionaryService
from features.dictionary.presentation.dictionary_dialog import DictionaryDialog
from features.document_matching.domain.processor_service import ProcessorService
from features.word_automation.logic.word_app_manager import WordAppManager
from features.word_automation.logic.temp_cleaner_service import TempCleanerService

from presentation.log_console import LogConsole

class MainWindow:
    """Main application window acting as the entry point and dependency root UI."""
    def __init__(self, root, app_settings: AppSettings):
        self.root = root
        self.settings = app_settings
        
        self.root.title("F12 Automation")
        self.root.geometry("1000x750")
        self.root.resizable(True, True)

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.icons = {}
        self._load_icons()

        self.is_dark_mode = True
        self.colors = THEMES['dark']
        self.root.configure(bg=self.colors['bg'])

        self.base_path = tk.StringVar()
        self.temp_path = tk.StringVar(value=tempfile.gettempdir())
        self.is_processing = False

        # Services
        self.dictionary_service = DictionaryService(self.settings.unified_medical_terms_path, self.settings.user_medical_terms_path)
        self.word_manager = WordAppManager()
        self.temp_cleaner = TempCleanerService()

        logger.add_callback(self._on_log)

        self._setup_styles()
        self._create_widgets()

    def _load_icons(self):
        icon_files = {
            'robot': 'f12-removebg-preview.png', 'moon': 'moon.png', 'sun': 'sun.png',
            'folder': 'folder.png', 'play': 'play.png', 'document': 'document.png',
            'clean': 'clean.png', 'trash': 'trash.png', 'log': 'log.png',
            'search': 'search.png', 'dictionary': 'dictionary.png', 'settings': 'edit.png',
            'copyright': 'copyright.png', 'icons8-f12-key-100': 'icons8-f12-key-100.png'
        }
        for key, filename in icon_files.items():
            try:
                icon_path = self.settings.icons_dir / filename
                if icon_path.exists():
                    img = Image.open(icon_path)
                    if key == 'robot': img = img.resize((30, 30), Image.LANCZOS)
                    elif key == 'search': img = img.resize((20, 20), Image.LANCZOS)
                    elif key == 'copyright': img = img.resize((10, 10), Image.LANCZOS)
                    else: img = img.resize((20, 20), Image.LANCZOS)
                    
                    if key == 'icons8-f12-key-100':
                        self.root.iconphoto(False, ImageTk.PhotoImage(img))
                    else:
                        self.icons[key] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Failed to load icon {filename}: {e}")
                self.icons[key] = None

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.colors = THEMES['dark' if self.is_dark_mode else 'light']
        self.root.configure(bg=self.colors['bg'])
        self._setup_styles()
        
        icon = self.icons['sun'] if self.is_dark_mode else self.icons['moon']
        if icon: self.theme_btn.config(image=icon, bg=self.colors['bg'], activebackground=self.colors['card_hover'])
        
        if hasattr(self, 'log_console'):
            self.log_console.apply_theme_colors(self.colors)
            
        if hasattr(self, 'entry_wrapper'):
            self.entry_wrapper.config(bg=self.colors['card_bg'], highlightbackground=self.colors.get('border', self.colors['accent']))
            self.base_entry.config(bg=self.colors['card_bg'], fg=self.colors['text'], insertbackground=self.colors['text'])

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        bg = self.colors['bg']
        card_bg = self.colors['card_bg']
        hover = self.colors['card_hover']
        accent = self.colors['accent']
        text = self.colors['text']
        text_secondary = self.colors['text_secondary']

        style.configure('Modern.TFrame', background=bg)
        style.configure('Card.TFrame', background=card_bg, relief='flat')
        style.configure('Title.TLabel', background=bg, foreground=text, font=('Segoe UI', 28, 'bold'))
        style.configure('Subtitle.TLabel', background=bg, foreground=text_secondary, font=('Segoe UI', 8))
        style.configure('CardTitle.TLabel', background=bg, foreground=text, font=('Segoe UI', 11, 'bold'))
        style.configure('CardLabel.TLabel', background=card_bg, foreground=text, font=('Segoe UI', 10, 'bold'))
        style.configure('Status.TLabel', background=card_bg, foreground=text_secondary, font=('Segoe UI', 10))
        
        style.configure('Secondary.TButton', background=card_bg, foreground=text, borderwidth=1, relief='flat', font=('Segoe UI', 9), padding=(8, 6))
        style.map('Secondary.TButton', background=[('active', hover)], foreground=[('active', text)])

        style.configure('Modern.Horizontal.TProgressbar', background=accent, troughcolor=card_bg, borderwidth=0, thickness=6)

        style.configure("Modern.TNotebook", background=card_bg, borderwidth=0, tabmargins=[8, 4, 8, 0])
        style.configure("Modern.TNotebook.Tab", background=card_bg, foreground=text_secondary, padding=(10, 10), font=('Segoe UI', 10, 'bold'), borderwidth=0)
        style.map("Modern.TNotebook.Tab", background=[('selected', accent), ('active', hover)], foreground=[('selected', 'white'), ('active', text)])

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, style='Modern.TFrame', padding="10")
        main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        main_frame.grid_rowconfigure(3, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        header_frame.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        header_frame.grid_columnconfigure(0, weight=1)
        
        title_frame = ttk.Frame(header_frame, style='Modern.TFrame')
        title_frame.grid(row=0, column=0, sticky='w')
        if self.icons.get('robot'): tk.Label(title_frame, image=self.icons['robot'], bg=self.colors['bg'], bd=0).grid(row=0, column=0)
        ttk.Label(title_frame, text=" Automation", style='Title.TLabel').grid(row=0, column=1)

        theme_icon = self.icons['sun'] if self.is_dark_mode else self.icons['moon']
        self.theme_btn = tk.Button(header_frame, image=theme_icon, command=self.toggle_theme, bg=self.colors['bg'], bd=0, relief='flat', cursor='hand2')
        self.theme_btn.grid(row=0, column=1, padx=8, pady=8, sticky='e')

        # Config Card
        config_card = ttk.Frame(main_frame, style='Card.TFrame', padding="10")
        config_card.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        config_card.grid_columnconfigure(0, weight=1)
        ttk.Label(config_card, text="Choose a Day", style='CardLabel.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 8))
        
        folder_frame = ttk.Frame(config_card, style='Card.TFrame')
        folder_frame.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        folder_frame.grid_columnconfigure(0, weight=1)
        
        self.entry_wrapper = tk.Frame(folder_frame, bg=self.colors['card_bg'], highlightbackground=self.colors.get('border', self.colors['accent']), highlightthickness=1)
        self.entry_wrapper.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        self.base_entry = tk.Entry(self.entry_wrapper, textvariable=self.base_path, bg=self.colors['card_bg'], fg=self.colors['text'], insertbackground=self.colors['text'], font=('Segoe UI', 10), relief='flat', bd=0)
        self.base_entry.pack(fill=tk.X, padx=12, pady=5)
        
        ttk.Button(folder_frame, text="Browse", command=lambda: self.browse_folder(self.base_path), style='Secondary.TButton', image=self.icons.get('folder'), compound=tk.LEFT).grid(row=0, column=1)

        # Actions
        action_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        action_frame.grid(row=2, column=0, sticky='ew', pady=(0, 5))
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(7, weight=1)
        
        self.process_btn = ttk.Button(action_frame, text="Start Processing", command=self.start_processing, style='Secondary.TButton', image=self.icons.get('play'), compound=tk.LEFT)
        self.process_btn.grid(row=0, column=1, padx=5)
        ttk.Button(action_frame, text="Close Word", command=self.close_word, style='Secondary.TButton', image=self.icons.get('document'), compound=tk.LEFT).grid(row=0, column=2, padx=5)
        ttk.Button(action_frame, text="Clean Temp", command=self.clean_temp, style='Secondary.TButton', image=self.icons.get('clean'), compound=tk.LEFT).grid(row=0, column=3, padx=5)
        ttk.Button(action_frame, text="Clear Log", command=lambda: self.log_console.clear(), style='Secondary.TButton', image=self.icons.get('trash'), compound=tk.LEFT).grid(row=0, column=4, padx=5)
        ttk.Button(action_frame, text="Manage Dictionary", command=self.open_dictionary, style='Secondary.TButton', image=self.icons.get('dictionary'), compound=tk.LEFT).grid(row=0, column=5, padx=5)

        # Log Console
        self.log_console = LogConsole(main_frame, self.colors, self.icons)
        
        # Progress
        progress_card = ttk.Frame(main_frame, style='Card.TFrame', padding="10")
        progress_card.grid(row=4, column=0, sticky='ew', pady=(5, 0))
        progress_card.grid_columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(progress_card, mode='indeterminate', style='Modern.Horizontal.TProgressbar')
        self.progress.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        self.status_label = ttk.Label(progress_card, text="● Ready to process", style='Status.TLabel')
        self.status_label.grid(row=1, column=0, sticky='w')

        # Footer
        footer_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        footer_frame.grid(row=5, column=0, sticky='ew', pady=(10, 0))
        ttk.Label(footer_frame, image=self.icons.get('copyright'), text="2025 F12 Automation Architecture", style='Subtitle.TLabel', compound=tk.LEFT).grid(row=0, column=0)

    def browse_folder(self, var):
        folder = filedialog.askdirectory(initialdir=var.get())
        if folder: var.set(folder)

    def _on_log(self, message: str, level: str):
        self.root.after(0, lambda: self.log_console.append_log(message, level))

    def update_status(self, text, processing=False):
        indicator = "◉" if processing else "●"
        self.root.after(0, lambda: self.status_label.config(text=f"{indicator} {text}"))

    def start_processing(self):
        if self.is_processing: return
        self.is_processing = True
        self.process_btn.config(state='disabled')
        self.progress.start(10)
        self.update_status("Processing documents...", processing=True)
        self.log_console.clear()
        
        thread = threading.Thread(target=self._run_processing, daemon=True)
        thread.start()

    def _run_processing(self):
        try:
            processor = ProcessorService(
                base_path=Path(self.base_path.get()),
                temp_path=Path(self.temp_path.get()),
                dictionary_service=self.dictionary_service
            )
            result = processor.process()
            self.root.after(0, lambda: messagebox.showinfo("Complete", f"Processed: {result.processed}\nErrors: {result.errors}"))
            self.update_status("Processing complete", processing=False)
        except Exception as e:
            logger.log(f"\n❌ CRITICAL ERROR: {e}", 'error')
            self.update_status("Processing failed", processing=False)
        finally:
            self.root.after(0, self._processing_finished)

    def _processing_finished(self):
        self.is_processing = False
        self.process_btn.config(state='normal')
        self.progress.stop()
        self.update_status("Ready", processing=False)

    def close_word(self):
        threading.Thread(target=self.word_manager.close_all_instances).start()

    def clean_temp(self):
        threading.Thread(target=self.temp_cleaner.clean_temp_folder, args=(Path(self.temp_path.get()),)).start()

    def open_dictionary(self):
        DictionaryDialog(self.root, self.dictionary_service, self.is_dark_mode, self.settings.icons_dir)
