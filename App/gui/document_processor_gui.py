import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import tempfile
from PIL import Image, ImageTk # Import Pillow modules
import json
from core.document_processor import DocumentProcessor
from core.word_utilities import WordUtilities
from core.dictionary_manager import DictionaryManager
from gui.dictionary_dialog import DictionaryDialog


class DocumentProcessorGUI:
    def __init__(self, root):
        self.log_buffer = []
        self.log_buffer_max_size = 50 
        self.current_file_log_context = []
        # --- Window setup ---
        self.root = root
        self.root.title("F12 Automation")
        self.config_file_path = Path(__file__).resolve().parents[1] / "config.json"
        self._load_config() # This will now load base_path
        self.root.geometry("1000x750")
        self.root.resizable(True, True)

        # Configure root grid weights for responsiveness
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # --- Load App Icon ---
        
        self.icons = {}
        
        try:
            icon_path = Path(__file__).resolve().parent.parent / "icons" / "icons8-f12-key-100.png"
            # Use Pillow to open and convert the image
            icon_image_pil = Image.open(icon_path)
            self.icon_image = ImageTk.PhotoImage(icon_image_pil)
            self.root.iconphoto(False, self.icon_image)
        except Exception as e:
            print(f"⚠️ Could not load app icon: {e}")

        self.load_icons()

        # --- Theme Management ---
        self.is_dark_mode = True
        self.themes = {
            'dark': {
                'bg': '#0f172a',
                'card_bg': '#1e293b',
                'card_hover': '#334155',
                'accent': '#3b82f6',
                'accent_hover': '#2563eb',
                'success': '#10b981',
                'error': '#ef4444',
                'warning': '#f59e0b',
                'text': "#ffffff",
                'text_secondary': '#94a3b8',
                'border': '#334155'
            },
            'light': {
                'bg': '#f8fafc',
                'card_bg': '#ffffff',
                'card_hover': '#f1f5f9',
                'accent': '#3b82f6',
                'accent_hover': '#2563eb',
                'success': '#059669',
                'error': '#dc2626',
                'warning': '#d97706',
                'text': '#0f172a',
                'text_secondary': '#64748b',
                'border': '#e2e8f0'
            }
        }

        self.colors = self.themes['dark']
        self.root.configure(bg=self.colors['bg'])

        # --- Paths & State ---
        # self.base_path is now initialized in _load_config
        self.temp_path = tk.StringVar(value=tempfile.gettempdir())
        self.is_processing = False
        self.search_var = tk.StringVar()
        self.all_log_entries = []

        # --- Dictionary Management ---
        # The user_medical_terms_path is now resolved in _load_config
        self.user_terms_file_path = Path(self.config.get("user_medical_terms_path"))
        # The DictionaryManager will handle the creation of the file if it doesn't exist at the specified path.
        
        self.dictionary_manager = DictionaryManager(self.user_terms_file_path, logger_callback=self.log)
        
        # --- Initialize UI ---
        self.setup_styles()
        self.create_widgets()

    def load_icons(self):
        """Load all PNG icons from the icons folder"""
        
        icons_dir = Path(__file__).resolve().parent.parent / "icons"
        
        icon_files = {
            'robot': 'f12-removebg-preview.png',
            'moon': 'moon.png',
            'sun': 'sun.png',
            'folder': 'folder.png',
            'play': 'play.png',
            'document': 'document.png',
            'clean': 'clean.png',
            'trash': 'trash.png',
            'log': 'log.png',
            'search': 'search.png',
            'dictionary': 'dictionary.png',
            'settings': 'edit.png',
            'copyright': 'copyright.png',
            
        }
        
        for key, filename in icon_files.items():
            try:
                icon_path = icons_dir / filename
                if icon_path.exists():
                    # Use Pillow to open and resize images
                    img_pil = Image.open(icon_path)
                    if key == 'robot':
                        img_pil = img_pil.resize((30, 30), Image.LANCZOS) # Larger for robot
                    elif key == 'search':
                        img_pil = img_pil.resize((20, 20), Image.LANCZOS) # Smaller for search
                    elif key == 'copyright':
    
                        img_pil = img_pil.resize((10, 10), Image.LANCZOS) # Smaller for search
                    else:
                        img_pil = img_pil.resize((20, 20), Image.LANCZOS) # Default size for others
                    self.icons[key] = ImageTk.PhotoImage(img_pil)
                else:
                    print(f"⚠️ Icon not found: {icon_path}")
                    self.icons[key] = None
            except Exception as e:
                print(f"⚠️ Could not load icon {filename}: {e}")
                self.icons[key] = None

    def toggle_theme(self):
        """Toggle between dark and light themes"""
        self.is_dark_mode = not self.is_dark_mode
        new_colors = self.themes['dark' if self.is_dark_mode else 'light']
        self.animate_theme_transition(self.colors, new_colors, 200, 10) # 200ms duration, 10 steps
        self.colors = new_colors # Update current colors after animation starts


    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb_color):
        return '#%02x%02x%02x' % rgb_color

    def interpolate_color(self, color1_hex, color2_hex, ratio):
        rgb1 = self.hex_to_rgb(color1_hex)
        rgb2 = self.hex_to_rgb(color2_hex)
        
        r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * ratio)
        g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * ratio)
        b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * ratio)
        
        return self.rgb_to_hex((r, g, b))

    def animate_theme_transition(self, start_colors, end_colors, duration_ms, steps):
        current_step = 0
        
        def _animate():
            nonlocal current_step
            if current_step > steps:
                self.apply_theme_step(end_colors) # Ensure final state is exactly the end theme
                return

            ratio = current_step / steps
            interpolated_colors = {}
            for key in start_colors:
                if key in end_colors:
                    interpolated_colors[key] = self.interpolate_color(start_colors[key], end_colors[key], ratio)
                else:
                    interpolated_colors[key] = start_colors[key] # Keep old if not in new

            self.apply_theme_step(interpolated_colors)
            
            current_step += 1
            if current_step <= steps:
                self.root.after(duration_ms // steps, _animate)

        _animate()

    def apply_theme_step(self, current_colors):
        """Apply the current theme to all widgets for a single animation step"""
        self.root.configure(bg=current_colors['bg'])
        self.setup_styles_step(current_colors) # Use a step-specific style setup

        icon = self.icons['sun'] if self.is_dark_mode else self.icons['moon']
        
        if icon:
            self.theme_btn.config(
                image=icon,
                bg=current_colors['bg'],
                activebackground=current_colors['card_hover']
            )
        
        self.all_log_frame.config(bg=current_colors['card_bg'])
        self.success_log_frame.config(bg=current_colors['card_bg'])
        self.error_log_frame.config(bg=current_colors['card_bg'])

        self.all_log_text.config(
            bg=current_colors['card_bg'],
            fg=current_colors['text'],
            insertbackground=current_colors['text'],
            selectbackground=current_colors['accent']
        )
        self.success_log_text.config(
            bg=current_colors['card_bg'],
            fg=current_colors['text'],
            insertbackground=current_colors['text'],
            selectbackground=current_colors['accent']
        )
        self.error_log_text.config(
            bg=current_colors['card_bg'],
            fg=current_colors['text'],
            insertbackground=current_colors['text'],
            selectbackground=current_colors['accent']
        )

        self.entry_wrapper.config(
            bg=current_colors['card_bg'],
            highlightbackground=current_colors['border'],
            highlightcolor=current_colors['accent']
        )
        self.base_entry.config(
            bg=current_colors['card_bg'],
            fg=current_colors['text'],
            insertbackground=current_colors['text']
        )

        if hasattr(self, 'search_entry'):
            self.search_entry.config(
                bg=current_colors['card_bg'],
                fg=current_colors['text'],
                insertbackground=current_colors['text'],
                highlightbackground=current_colors['border'],
                highlightcolor=current_colors['accent']
            )

        self.all_log_text.tag_config('success', foreground=current_colors['success'])
        self.all_log_text.tag_config('warning', foreground=current_colors['warning'])
        self.all_log_text.tag_config('info', foreground=current_colors['text_secondary'])
        self.all_log_text.tag_config('error', foreground=current_colors['error'])
        self.success_log_text.tag_config('success', foreground=current_colors['success'])
        self.success_log_text.tag_config('warning', foreground=current_colors['warning'])
        self.success_log_text.tag_config('info', foreground=current_colors['text_secondary'])
        self.error_log_text.tag_config('error', foreground=current_colors['error'])
        self.error_log_text.tag_config('info', foreground=current_colors['text_secondary'])
        self.error_log_text.tag_config('warning', foreground=current_colors['warning'])
        self.error_log_text.tag_config('success', foreground=current_colors['success'])

        # Treeview styles for the main window (if any remain)
        style = ttk.Style()
        style.configure('Modern.Treeview.Heading',
                        background=current_colors['accent'],
                        foreground='white',
                        font=('Segoe UI', 10, 'bold'),
                        relief='flat')
        style.configure('Modern.Treeview',
                        background=current_colors['card_bg'],
                        foreground=current_colors['text'],
                        fieldbackground=current_colors['card_bg'],
                        font=('Segoe UI', 10),
                        borderwidth=0,
                        rowheight=25)
        style.map('Modern.Treeview',
                  background=[('selected', current_colors['accent'])],
                  foreground=[('selected', 'white')])
        style.layout("Modern.Treeview", [('Modern.Treeview.treearea', {'sticky': 'nswe'})])

    def setup_styles(self):
        # This method will now be called once at init and then setup_styles_step will be used for transitions
        self.setup_styles_step(self.colors)

    def setup_styles_step(self, current_colors):
        style = ttk.Style()
        style.theme_use('clam')
        
        bg = current_colors['bg']
        card_bg = current_colors['card_bg']
        hover = current_colors['card_hover']
        accent = current_colors['accent']
        text = current_colors['text']
        text_secondary = current_colors['text_secondary']

        style.configure('Modern.TFrame', background=bg)
        style.configure('Card.TFrame', background=card_bg, relief='flat')
        
        style.configure('Modern.TLabel',
                        background=bg,
                        foreground=text,
                        font=('Segoe UI', 10))
        
        style.configure('Title.TLabel',
                        background=bg,
                        foreground=text,
                        font=('Segoe UI', 28, 'bold'))
        
        style.configure('Subtitle.TLabel',
                        background=bg,
                        foreground=text_secondary,
                        font=('Segoe UI', 8))
        
        style.configure('CardTitle.TLabel',
                        background=bg,
                        foreground=text,
                        font=('Segoe UI', 11, 'bold'))
        
        style.configure('CardLabel.TLabel',
                        background=card_bg,
                        foreground=text,
                        font=('Segoe UI', 10, 'bold'))
        
        style.configure('Status.TLabel',
                        background=card_bg,
                        foreground=text_secondary,
                        font=('Segoe UI', 10))
        
        style.configure('Secondary.TButton',
                        background=card_bg,
                        foreground=text,
                        borderwidth=1,
                        relief='flat',
                        font=('Segoe UI', 9),
                        padding=(8, 6))
        style.map('Secondary.TButton',
                background=[('active', hover)],
                foreground=[('active', text)])

        style.configure('Modern.Horizontal.TProgressbar',
                        background=accent,
                        troughcolor=card_bg,
                        borderwidth=0,
                        thickness=6)
        
        style.layout("Modern.TNotebook", [("Notebook.client", {"sticky": "nswe"})])
        style.layout("Modern.TNotebook.Tab", [
            ("Notebook.tab", {
                "sticky": "nswe",
                "children": [
                    ("Notebook.padding", {
                        "side": "top",
                        "sticky": "nswe",
                        "children": [
                            ("Notebook.label", {"side": "top", "sticky": ""})
                        ]
                    })
                ]
            })
        ])

        style.configure("Modern.TNotebook",
                        background=card_bg,
                        borderwidth=0,
                        tabmargins=[8, 4, 8, 0])
        
        style.configure("Modern.TNotebook.Tab",
                        background=card_bg,
                        foreground=text_secondary,
                        padding=(10, 10),
                        font=('Segoe UI', 10, 'bold'),
                        borderwidth=0)
        
        style.map("Modern.TNotebook.Tab",
                background=[
                    ('selected', accent),
                    ('active', hover)
                ],
                foreground=[
                    ('selected', 'white'),
                    ('active', text)
                ],
                expand=[('selected', [1, 1, 1, 0])])
        
        style.configure("Modern.TNotebook.Tab",
                        focuscolor=accent,
                        relief='flat')

        style.configure("TNotebook", borderwidth=0, relief="flat")

    def create_widgets(self):
        # Main container with grid
        main_frame = ttk.Frame(self.root, style='Modern.TFrame', padding="10")
        main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        
        # Configure main frame grid weights
        main_frame.grid_rowconfigure(3, weight=1)  # Log section gets extra space
        main_frame.grid_columnconfigure(0, weight=1)
        
        # ===== HEADER =====
        header_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        header_frame.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        header_frame.grid_columnconfigure(0, weight=1)  # Left side expands
        
        title_container = ttk.Frame(header_frame, style='Modern.TFrame')
        title_container.grid(row=0, column=0, sticky='w')
        
        title_frame = ttk.Frame(title_container, style='Modern.TFrame')
        title_frame.grid(row=0, column=0, sticky='w')
        
        if self.icons.get('robot'):
            icon_label = tk.Label(title_frame, image=self.icons['robot'], 
                                bg=self.colors['bg'], bd=0)
            icon_label.grid(row=0, column=0, padx=(0, 0))
        
        ttk.Label(title_frame, text=" Automation", style='Title.TLabel').grid(row=0, column=1, sticky='w')


        theme_container = ttk.Frame(header_frame, style='Modern.TFrame')
        theme_container.grid(row=0, column=1, sticky='e', padx=(0, 0))

        theme_icon = self.icons['sun'] if self.is_dark_mode else self.icons['moon']
        
        self.theme_btn = tk.Button(
            theme_container,
            image=theme_icon if theme_icon else None,
            text="" if theme_icon else "Toggle",
            command=self.toggle_theme,
            bg=self.colors['bg'],
            bd=0,
            relief='flat',
            cursor='hand2',
            activebackground=self.colors['card_hover']
        )
        self.theme_btn.grid(row=0, column=0, padx=8, pady=8)
        
        # ===== CONFIGURATION CARD =====
        config_card = ttk.Frame(main_frame, style='Card.TFrame', padding="10")
        config_card.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        config_card.grid_columnconfigure(0, weight=1)
        
        ttk.Label(config_card, text="Choose a Day", style='CardLabel.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 8))
        
        folder_input_frame = ttk.Frame(config_card, style='Card.TFrame')
        folder_input_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        folder_input_frame.grid_columnconfigure(0, weight=1)
        
        self.entry_wrapper = tk.Frame(folder_input_frame, bg=self.colors['card_bg'], 
                                highlightbackground=self.colors['border'], 
                                highlightthickness=1, highlightcolor=self.colors['accent'])
        self.entry_wrapper.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        
        self.base_entry = tk.Entry(self.entry_wrapper, textvariable=self.base_path,
                                   bg=self.colors['card_bg'], fg=self.colors['text'],
                                   insertbackground=self.colors['text'],
                                   font=('Segoe UI', 10), relief='flat', bd=0)
        self.base_entry.pack(fill=tk.X, padx=12, pady=5)
        
        browse_btn = ttk.Button(folder_input_frame, text="Browse",
                               command=lambda: self.browse_folder(self.base_path),
                               style='Secondary.TButton', 
                               image=self.icons.get('folder') if self.icons.get('folder') else None,
                               compound=tk.LEFT)
        browse_btn.grid(row=0, column=1, sticky='w')
        
       # ===== ACTION BUTTONS =====
        action_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        action_frame.grid(row=2, column=0, sticky='ew', pady=(0, 5))

        # Make columns 0 and 5 expand (for centering)
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(7, weight=1) # Adjusted for new button

        # Buttons start at column 1
        self.process_btn = ttk.Button(
            action_frame, text="Start Processing",
            command=self.start_processing,
            style='Secondary.TButton',
            image=self.icons.get('play'),
            compound=tk.LEFT
        )
        self.process_btn.grid(row=0, column=1, padx=5)

        ttk.Button(
            action_frame, text="Close Word",
            command=self.close_word_instances,
            style='Secondary.TButton',
            image=self.icons.get('document'),
            compound=tk.LEFT
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            action_frame, text="Clean Temp",
            command=self.clean_temp_folder,
            style='Secondary.TButton',
            image=self.icons.get('clean'),
            compound=tk.LEFT
        ).grid(row=0, column=3, padx=5)

        ttk.Button(
            action_frame, text="Clear Log",
            command=self.clear_log,
            style='Secondary.TButton',
            image=self.icons.get('trash'),
            compound=tk.LEFT
        ).grid(row=0, column=4, padx=5)
        
        ttk.Button(
            action_frame, text="Manage Dictionary",
            command=self.open_dictionary_dialog,
            style='Secondary.TButton',
            image=self.icons.get('dictionary'), # Reusing search icon for dictionary
            compound=tk.LEFT
        ).grid(row=0, column=5, padx=5)

        ttk.Button(
            action_frame, text="Settings",
            command=self.open_settings_dialog,
            style='Secondary.TButton',
            image=self.icons.get('settings'),
            compound=tk.LEFT
        ).grid(row=0, column=6, padx=5)


        # ===== LOG SECTION =====
        log_section = ttk.Frame(main_frame, style='Modern.TFrame')
        log_section.grid(row=3, column=0, sticky='nsew', pady=(0, 10))
        log_section.grid_rowconfigure(1, weight=1)
        log_section.grid_columnconfigure(0, weight=1)
        log_section.grid_propagate(False)  # Prevent frame from shrinking below minimum
        log_section.update_idletasks()  # Force layout calculation
        log_section.config(height=300)  # Minimum height for log section
        
        log_title_frame = ttk.Frame(log_section, style='Modern.TFrame')
        log_title_frame.grid(row=0, column=0, sticky='w', pady=(0, 8))
        
        if self.icons.get('log'):
            log_icon_label = tk.Label(log_title_frame, image=self.icons['log'], 
                                     bg=self.colors['bg'], bd=0)
            log_icon_label.grid(row=0, column=0, padx=(0, 5))
        
        ttk.Label(log_title_frame, text="Processing Log", style='CardTitle.TLabel').grid(row=0, column=1, sticky='w')
        
        log_card = ttk.Frame(log_section, style='Card.TFrame', padding="10")
        log_card.grid(row=1, column=0, sticky='nsew')
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_propagate(False)  # Prevent shrinking
        log_card.config(width=400, height=250)  # Minimum dimensions
        
        # Search bar
        search_bar_frame = ttk.Frame(log_card, style='Card.TFrame')
        search_bar_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        search_bar_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = tk.Entry(search_bar_frame, textvariable=self.search_var,
                             bg=self.colors['card_bg'], fg=self.colors['text'],
                             insertbackground=self.colors['text'],
                             font=('Segoe UI', 10), relief='flat', bd=0,
                             highlightbackground=self.colors['border'],
                             highlightthickness=1, highlightcolor=self.colors['accent'])
        self.search_entry.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        self.search_entry.bind("<Return>", lambda event=None: self.search_logs())

        search_btn = ttk.Button(search_bar_frame, text="Search",
                                command=self.search_logs,
                                style='Secondary.TButton',
                                image=self.icons.get('search') if self.icons.get('search') else None,
                                compound=tk.LEFT)
        search_btn.grid(row=0, column=1, sticky='e')
        
        # Notebook
        self.main_notebook = ttk.Notebook(log_card, style="Modern.TNotebook")
        self.main_notebook.grid(row=1, column=0, sticky='nsew', padx=2, pady=2)

        # --- Log Tabs ---
        # All Log Tab
        self.all_log_frame = tk.Frame(self.main_notebook, bg=self.colors['card_bg'])
        self.main_notebook.add(self.all_log_frame, text="All")
        self.all_log_frame.grid_rowconfigure(0, weight=1)
        self.all_log_frame.grid_columnconfigure(0, weight=1)

        self.all_log_text = scrolledtext.ScrolledText(
            self.all_log_frame,
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            font=('Consolas', 10),
            relief='flat',
            bd=0,
            insertbackground=self.colors['text'],
            selectbackground=self.colors['accent'],
            selectforeground='white',
            wrap=tk.WORD,
        )
        self.all_log_text.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
        self.all_log_text.bind("<Key>", lambda e: "break")
        self.all_log_text.tag_config('success', foreground=self.colors['success'])
        self.all_log_text.tag_config('info', foreground=self.colors['text_secondary'])
        self.all_log_text.tag_config('warning', foreground=self.colors['warning'])
        self.all_log_text.tag_config('error', foreground=self.colors['error'])

        # Success Log Tab
        self.success_log_frame = tk.Frame(self.main_notebook, bg=self.colors['card_bg'])
        self.main_notebook.add(self.success_log_frame, text="Success")
        self.success_log_frame.grid_rowconfigure(0, weight=1)
        self.success_log_frame.grid_columnconfigure(0, weight=1)

        self.success_log_text = scrolledtext.ScrolledText(
            self.success_log_frame,
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            font=('Consolas', 10),
            relief='flat',
            bd=0,
            insertbackground=self.colors['text'],
            selectbackground=self.colors['accent'],
            selectforeground='white',
            wrap=tk.WORD,
        )
        self.success_log_text.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
        self.success_log_text.bind("<Key>", lambda e: "break")
        self.success_log_text.tag_config('success', foreground=self.colors['success'])
        self.success_log_text.tag_config('info', foreground=self.colors['text_secondary'])
        self.success_log_text.tag_config('warning', foreground=self.colors['warning'])

        # Error Log Tab
        self.error_log_frame = tk.Frame(self.main_notebook, bg=self.colors['card_bg'])
        self.main_notebook.add(self.error_log_frame, text="Errors")
        self.error_log_frame.grid_rowconfigure(0, weight=1)
        self.error_log_frame.grid_columnconfigure(0, weight=1)

        self.error_log_text = scrolledtext.ScrolledText(
            self.error_log_frame,
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            font=('Consolas', 10),
            relief='flat',
            bd=0,
            insertbackground=self.colors['text'],
            selectbackground=self.colors['accent'],
            selectforeground='white',
            wrap=tk.WORD,
        )
        self.error_log_text.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
        self.error_log_text.bind("<Key>", lambda e: "break")
        self.error_log_text.tag_config('error', foreground=self.colors['error'])
        self.error_log_text.tag_config('info', foreground=self.colors['text_secondary'])
        self.error_log_text.tag_config('warning', foreground=self.colors['warning'])
        self.error_log_text.tag_config('success', foreground=self.colors['success'])

        # ===== PROGRESS SECTION =====
        progress_card = ttk.Frame(main_frame, style='Card.TFrame', padding="10")
        progress_card.grid(row=4, column=0, sticky='ew', pady=(5, 0))
        progress_card.grid_columnconfigure(0, weight=1)
        
        self.progress = ttk.Progressbar(
            progress_card, mode='indeterminate',
            style='Modern.Horizontal.TProgressbar'
        )
        self.progress.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        self.status_label = ttk.Label(
            progress_card,
            text="● Ready to process",
            style='Status.TLabel'
        )
        self.status_label.grid(row=1, column=0, sticky='w')

        # ===== FOOTER =====
        footer_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        footer_frame.grid(row=5, column=0, sticky='ew', pady=(10, 0))
        footer_frame.grid_columnconfigure(0, weight=1)

        footer_label = ttk.Label(
    footer_frame,
    image=self.icons.get('copyright') if self.icons.get('copyright') else None,
    text="2025 Ahmed Azzi | mrahmedazzi@gmail.com",
    style='Subtitle.TLabel',
    compound=tk.LEFT  # Add this line
)
        footer_label.grid(row=0, column=0, sticky='ew')

    def browse_folder(self, var):
        folder = filedialog.askdirectory(initialdir=var.get())
        if folder:
            var.set(folder)

    def log(self, message, tag='info'):
        def _log():
            self.all_log_text.insert(tk.END, message + '\n', tag)
            self.all_log_text.see(tk.END)

            self.log_buffer.append((message, tag))
            if len(self.log_buffer) > self.log_buffer_max_size:
                self.log_buffer.pop(0)

            self.all_log_entries.append((message, tag))

            if "🔄 [" in message and "Reading:" in message:
                self.current_file_log_context = []
            self.current_file_log_context.append((message, tag))

            if tag == 'success':
                for ctx_msg, ctx_tag in self.current_file_log_context:
                    self.success_log_text.insert(tk.END, ctx_msg + '\n', ctx_tag)
                self.success_log_text.see(tk.END)
                self.current_file_log_context = []
            elif tag == 'error' or tag == 'summary_error':
                if "❌ Errors:" in message:
                    self.error_log_text.insert(tk.END, message + '\n', tag)
                else:
                    for ctx_msg, ctx_tag in self.current_file_log_context:
                        self.error_log_text.insert(tk.END, ctx_msg + '\n', ctx_tag)
                    self.error_log_text.see(tk.END)
                self.current_file_log_context = []
            elif tag == 'warning' and ("No confident match found" in message or "No match found for patient" in message):
                for ctx_msg, ctx_tag in self.current_file_log_context:
                    self.error_log_text.insert(tk.END, ctx_msg + '\n', ctx_tag)
                self.error_log_text.see(tk.END)
                self.current_file_log_context = []
        self.root.after(0, _log)

    def clear_log(self):
        self.all_log_text.delete(1.0, tk.END)
        self.success_log_text.delete(1.0, tk.END)
        self.error_log_text.delete(1.0, tk.END)
        self.log_buffer.clear()
        self.current_file_log_context.clear()
        self.log("Log cleared.\n", 'info')

    def update_status(self, text, processing=False):
        def _update():
            status_indicator = "◉" if processing else "●"
            self.status_label.config(text=f"{status_indicator} {text}")
        self.root.after(0, _update)

    def start_processing(self):
        if self.is_processing:
            return
        self.is_processing = True
        self.process_btn.config(state='disabled')
        self.progress.start(10)
        self.update_status("Processing documents...", processing=True)
        self.clear_log()
        thread = threading.Thread(target=self.run_processing, daemon=True)
        thread.start()

    def run_processing(self):
        try:
            processor = DocumentProcessor(
                base_path=Path(self.base_path.get()),
                temp_path=Path(self.temp_path.get()),
                logger_callback=self.log
            )
            result = processor.process()
            self.root.after(0, lambda: messagebox.showinfo(
                "Processing Complete",
                f"✓ Processing finished successfully!\n\n"
                f"Processed: {result['processed']}\n"
                f"Errors: {result['errors']}"
            ))
            self.update_status("Processing complete", processing=False)
        except Exception as e:
            self.log(f"\n❌ CRITICAL ERROR: {e}", 'error')
            import traceback
            self.log(traceback.format_exc(), 'error')
            self.update_status("Processing failed", processing=False)
        finally:
            self.root.after(0, self.processing_finished)

    def search_logs(self):
        """Search logs based on the input term."""
        search_term = self.search_var.get().lower()
        
        self.all_log_text.delete("1.0", tk.END)
        
        if not search_term:
            for msg, tag in self.all_log_entries:
                self.all_log_text.insert(tk.END, msg + '\n', tag)
        else:
            filtered_logs = [
                (msg, tag) for msg, tag in self.all_log_entries
                if search_term in msg.lower()
            ]
            for msg, tag in filtered_logs:
                self.all_log_text.insert(tk.END, msg + '\n', tag)
        
        self.all_log_text.see(tk.END)

    def processing_finished(self):
        self.is_processing = False
        self.process_btn.config(state='normal')
        self.progress.stop()
        self.update_status("Ready to process", processing=False)

    def close_word_instances(self):
        """Close all open Microsoft Word instances"""
        def _close():
            try:
                utilities = WordUtilities(logger_callback=self.log)
                result = utilities.close_all_word_instances()
                
                if result["error"]:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error",
                        f"Failed to close Word instances:\n{result['error']}"
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Word Closed",
                        f"All Word instances have been closed successfully.\n\nClosed: {result['closed']} document(s)"
                    ))
            except Exception as e:
                self.log(f"❌ Unexpected error: {e}", 'error')
                self.root.after(0, lambda: messagebox.showerror(
                    "Error",
                    f"An unexpected error occurred:\n{e}"
                ))
        
        thread = threading.Thread(target=_close, daemon=True)
        thread.start()

    def clean_temp_folder(self):
        """clean all files from temp folder"""
  
        
        def _clean():
            try:
                utilities = WordUtilities(logger_callback=self.log)
                temp_path = Path(self.temp_path.get())
                
                result = utilities.clean_temp_folder(temp_path)
                
                if result["error"]:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Cleanup Error",
                        f"An error occurred during cleanup:\n{result['error']}"
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Cleanup Complete",
                        f"Temp folder cleaned successfully!\n\nDeleted: {result['deleted']} file(s)\nErrors: {result['errors']}"
                    ))
            except Exception as e:
                self.log(f"❌ Unexpected error: {e}", 'error')
                import traceback
                self.log(traceback.format_exc(), 'error')
                self.root.after(0, lambda: messagebox.showerror(
                    "Error",
                    f"An unexpected error occurred:\n{e}"
                ))
        
        thread = threading.Thread(target=_clean, daemon=True)
        thread.start()

    def open_dictionary_dialog(self):
        """Opens the modern dictionary management dialog."""
        dialog = DictionaryDialog(
            self.root,
            self.dictionary_manager,
            self.log,
            self.themes,
            self.is_dark_mode,
            parent_gui=self,  # Pass reference to DocumentProcessorGUI instance
            user_terms_file_path=self.user_terms_file_path # Pass the current path
        )
        self.root.wait_window(dialog)

    def open_settings_dialog(self):
        """Opens a dialog to configure application settings."""
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("Settings")
        settings_dialog.geometry("600x150")
        settings_dialog.transient(self.root)
        settings_dialog.grab_set()
        settings_dialog.resizable(False, False)

        dialog_width = 600
        dialog_height = 150

        # Get parent's position and size
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()

        # Calculate centered position
        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)

        # Apply the new geometry
        settings_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        dialog_colors = self.themes['dark' if self.is_dark_mode else 'light']
        settings_dialog.configure(bg=dialog_colors['bg'])

        main_frame = ttk.Frame(settings_dialog, style='Modern.TFrame', padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_columnconfigure(0, weight=1)

        # Dictionary Path
        ttk.Label(main_frame, text="User Dictionary Path", style='CardLabel.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 8))
        dict_path_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        dict_path_frame.grid(row=1, column=0, columnspan=2, sticky='ew')
        dict_path_frame.grid_columnconfigure(0, weight=1)
        new_dict_path = tk.StringVar(value=self.user_terms_file_path)
        dict_entry = tk.Entry(dict_path_frame, textvariable=new_dict_path,
                         bg=dialog_colors['card_bg'], fg=dialog_colors['text'],
                         insertbackground=dialog_colors['text'],
                         font=('Segoe UI', 10), relief='flat', bd=0)
        dict_entry.grid(row=0, column=0, sticky='ew', padx=(0, 10), ipady=4)
        def browse_dict():
            file = filedialog.askopenfilename(initialdir=Path(new_dict_path.get()).parent, filetypes=[("JSON files", "*.json")])
            if file:
                new_dict_path.set(file)
        dict_browse_btn = ttk.Button(dict_path_frame, text="Browse", command=browse_dict, style='Secondary.TButton')
        dict_browse_btn.grid(row=0, column=1)


        button_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        button_frame.grid(row=2, column=0, columnspan=2, sticky='e', pady=(10, 0))

        def save_settings():
            # Save Dictionary Path and update manager
            new_path_obj = Path(new_dict_path.get())
            self.config['user_medical_terms_path'] = str(new_path_obj)
            self.update_dictionary_manager(new_path_obj)
            
            self._save_config(self.config)
            settings_dialog.destroy()

        save_btn = ttk.Button(button_frame, text="Save", command=save_settings, style='Secondary.TButton')
        save_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = ttk.Button(button_frame, text="Cancel", command=settings_dialog.destroy, style='Secondary.TButton')
        cancel_btn.pack(side=tk.LEFT)

    def _load_config(self):
        """Loads configuration from config.json."""
        self.config = {}
        default_base_path = r"\\22dellw10\22\22Mega\01Instances"
        
        if self.config_file_path.exists():
            try:
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except json.JSONDecodeError:
                self.log("Error: Could not decode config.json. File might be corrupted.", 'error')
            except Exception as e:
                self.log(f"An unexpected error occurred while loading config: {e}", 'error')
        else:
            self.log("Info: config.json not found. Using default settings.", 'info')
            # Create a default config if it doesn't exist
            self._save_config({
                "user_medical_terms_path": str(Path(default_base_path) / "data" / "user_medical_terms.json"),
                "base_path": default_base_path
            })
            self._load_config() # Reload after creating default
            return

        # Initialize base_path from config or use default
        self.base_path = tk.StringVar(value=self.config.get('base_path', default_base_path))

        # Resolve user_medical_terms_path: if relative, resolve against default_base_path
        user_terms_path_from_config = self.config.get("user_medical_terms_path", "data/user_medical_terms.json")
        temp_path_obj = Path(user_terms_path_from_config)
        if not temp_path_obj.is_absolute():
            self.config['user_medical_terms_path'] = str(Path(default_base_path) / temp_path_obj)
            # Save the updated config back to file to persist the absolute path
            self._save_config(self.config)


    def _save_config(self, config_data):
        """Saves configuration to config.json."""
        try:
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            self.log(f"✓ Configuration saved to {self.config_file_path}", 'success')
        except Exception as e:
            self.log(f"Error: Could not save configuration to {self.config_file_path}: {e}", 'error')

    def update_dictionary_manager(self, new_path: Path):
        """Updates the DictionaryManager instance with a new path."""
        self.user_terms_file_path = new_path
        self.dictionary_manager = DictionaryManager(self.user_terms_file_path, logger_callback=self.log)
        self.log(f"DictionaryManager updated to use new path: {new_path}", 'info')
