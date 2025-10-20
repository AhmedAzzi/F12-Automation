import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from PIL import Image, ImageTk

import json

class DictionaryDialog(tk.Toplevel):
    def __init__(self, parent, dictionary_manager, log_callback, themes, is_dark_mode, parent_gui=None, user_terms_file_path=None):
        super().__init__(parent)
        self.parent = parent
        self.parent_gui = None # Initialize to None
        self.parent_gui = parent_gui  # Reference to the DocumentProcessorGUI instance
        self.dictionary_manager = dictionary_manager
        self.log = log_callback
        self.themes = themes
        self.config_file_path = Path(__file__).resolve().parents[1] / "config.json"
        self.user_terms_file_path_var = tk.StringVar()
        self.user_terms_file_path_var.set(user_terms_file_path if user_terms_file_path else self._load_user_terms_path_from_config())

        self.title("Manage User Dictionary")
        self.geometry("700x800")
        self.resizable(True, True)
        self.minsize(600, 700)

        # Configure grid weights for responsiveness
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.new_main_term_var = tk.StringVar()
        self.new_synonyms_var = tk.StringVar()

        # Get initial theme from parent_gui
        if self.parent_gui:
            self.is_dark_mode = self.parent_gui.is_dark_mode
            self.colors = self.themes['dark' if self.is_dark_mode else 'light']
        else:
            self.is_dark_mode = is_dark_mode
            self.colors = self.themes['dark' if self.is_dark_mode else 'light']

        self.configure(bg=self.colors['bg'])

        self.setup_styles()
        self.load_icons()
        self.create_widgets()
        self.load_user_terms_to_treeview()
        
        # Bind entry widgets for live validation visual feedback
        self.main_term_entry.bind('<FocusIn>', self._on_entry_focus)
        self.main_term_entry.bind('<FocusOut>', self._on_entry_blur)
        self.synonyms_entry.bind('<FocusIn>', self._on_entry_focus)
        self.synonyms_entry.bind('<FocusOut>', self._on_entry_blur)
        # Removed polling for theme changes to prevent main window dizziness
        # self._check_theme_changed()

    def _populate_fields_from_selection(self):
        """Populate input fields when a term is selected in the treeview, triggered by a button."""
        selected_item = self.terms_tree.focus()
        if selected_item:
            values = self.terms_tree.item(selected_item, 'values')
            if values:
                self.new_main_term_var.set(values[0])
                self.new_synonyms_var.set(values[1])
        else:
            messagebox.showwarning("Selection Error", "Please select a term to edit.", parent=self)


    def _on_entry_focus(self, event):
        event.widget.config(highlightthickness=2)

    def _on_entry_blur(self, event):
        event.widget.config(highlightthickness=1)

    def load_icons(self):
        """Load all PNG icons from the icons folder"""
        self.icons = {} # Initialize the icons dictionary
        
        icons_dir = Path(__file__).resolve().parent.parent / "icons"
        
        icon_files = {
            'document': 'document.png',
            'trash': 'trash.png',
            'dictionary': 'dictionary.png',
            'add': 'add.png',
            'edit': 'edit.png'
        }
        
        for key, filename in icon_files.items():
            try:
                icon_path = icons_dir / filename
                if icon_path.exists():
                    img_pil = Image.open(icon_path)
                    if key == 'dictionary':
                        img_pil = img_pil.resize((30, 30), Image.LANCZOS) # Larger for dictionary icon
                    else:
                        img_pil = img_pil.resize((20, 20), Image.LANCZOS) # Default size for others
                    self.icons[key] = ImageTk.PhotoImage(img_pil)
                else:
                    print(f"⚠️ Icon not found: {icon_path}")
                    self.icons[key] = None
            except Exception as e:
                print(f"⚠️ Could not load icon {filename}: {e}")
                self.icons[key] = None

    def setup_styles(self):
        style = ttk.Style(self)
        # style.theme_use('clam') # The parent GUI already sets the theme
        
        bg = self.colors['bg']
        card_bg = self.colors['card_bg']
        hover = self.colors['card_hover']
        accent = self.colors['accent']
        text = self.colors['text']
        text_secondary = self.colors['text_secondary']
        border = self.colors.get('border', accent)

        style.configure('Dialog.Modern.TFrame', background=bg)
        style.configure('Dialog.Card.TFrame', background=card_bg, relief='flat')
        style.configure('Dialog.GradientHeader.TFrame', background=accent, relief='flat')
        
        style.configure('Dialog.Modern.TLabel',
                        background=bg,
                        foreground=text,
                        font=('Segoe UI', 10))
        
        style.configure('Dialog.Title.TLabel',
                        background=bg,
                        foreground=text,
                        font=('Segoe UI', 20, 'bold'))
        
        style.configure('Dialog.Subtitle.TLabel',
                        background=bg,
                        foreground=text_secondary,
                        font=('Segoe UI', 11))
        
        style.configure('Dialog.CardTitle.TLabel',
                        background=card_bg,
                        foreground=text,
                        font=('Segoe UI', 12, 'bold'))
        
        style.configure('Dialog.CardLabel.TLabel',
                        background=card_bg,
                        foreground=text_secondary,
                        font=('Segoe UI', 9))
        
        style.configure('Dialog.Status.TLabel',
                        background=card_bg,
                        foreground=text_secondary,
                        font=('Segoe UI', 9, 'italic'))
        
        style.configure('Dialog.Primary.TButton',
                        background=card_bg,
                        foreground=text,
                        borderwidth=1,
                        relief='flat',
                        font=('Segoe UI', 9),
                        padding=(8, 6))
        style.map('Dialog.Primary.TButton',
                background=[('active', hover)],
                foreground=[('active', text)])

        style.configure('Dialog.Secondary.TButton',
                        background=card_bg,
                        foreground=text,
                        borderwidth=1,
                        relief='flat',
                        font=('Segoe UI', 9),
                        padding=(10, 6))
        style.map('Dialog.Secondary.TButton',
                background=[('active', hover)],
                foreground=[('active', text)])

        style.configure('Dialog.Danger.TButton',
                        background='#ff6b6b',
                        foreground='white',
                        borderwidth=0,
                        relief='flat',
                        font=('Segoe UI', 9),
                        padding=(10, 6))
        style.map('Dialog.Danger.TButton',
                background=[('active', '#ff5252'),
                           ('pressed', '#ff4444')],
                foreground=[('active', 'white')])

        # Treeview styles
        style.configure('Dialog.Modern.Treeview.Heading',
                        background=card_bg,
                        foreground=text_secondary,
                        font=('Segoe UI', 10, 'bold'),
                        relief='flat',
                        borderwidth=0)
        style.map('Dialog.Modern.Treeview.Heading',
                  background=[('active', card_bg)],
                  foreground=[('active', text_secondary)])
        style.configure('Dialog.Modern.Treeview',
                        background=card_bg,
                        foreground=text,
                        fieldbackground=card_bg,
                        font=('Segoe UI', 10),
                        borderwidth=0,
                        rowheight=28)
        style.map('Dialog.Modern.Treeview',
                  background=[('selected', accent)],
                  foreground=[('selected', 'white')])
        style.layout("Dialog.Modern.Treeview", [('Dialog.Modern.Treeview.treearea', {'sticky': 'nswe'})])

    def _lighten_color(self, hex_color, factor):
        """Lighten a hex color by a factor"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            r = min(int(r * factor), 255)
            g = min(int(g * factor), 255)
            b = min(int(b * factor), 255)
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return hex_color

    def apply_theme(self):
        self.colors = self.themes['dark' if self.is_dark_mode else 'light']
        self.configure(bg=self.colors['bg'])
        self.setup_styles()

        # Update entry widgets
        self.main_term_entry.config(
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            highlightbackground=self.colors.get('border', self.colors['accent']),
            highlightcolor=self.colors['accent']
        )
        self.synonyms_entry.config(
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            highlightbackground=self.colors.get('border', self.colors['accent']),
            highlightcolor=self.colors['accent']
        )
        
        # Update main frames
        self.main_frame.config(style='Dialog.Modern.TFrame')
        self.add_term_card.config(style='Dialog.Card.TFrame')
        self.current_terms_card.config(style='Dialog.Card.TFrame')

    def create_widgets(self):
        self.main_frame = ttk.Frame(self, style='Dialog.Modern.TFrame', padding="0")
        self.main_frame.grid(row=0, column=0, sticky='nsew')
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Header section with icon-like styling
        header_frame = ttk.Frame(self.main_frame, style='Dialog.Modern.TFrame', padding="10")
        header_frame.grid(row=0, column=0, sticky='ew')
        header_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(header_frame, text="Dictionary Manager", 
                 image=self.icons.get('dictionary'), compound='left',
                 style='Dialog.Title.TLabel').grid(row=0, column=0, sticky='w')

        # Content frame with padding
        content_frame = ttk.Frame(self.main_frame, style='Dialog.Modern.TFrame', padding="10")
        content_frame.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=1) # Adjusted row for new path setting card

        # Add New Term Card - Enhanced
        self.add_term_card = ttk.Frame(content_frame, style='Dialog.Card.TFrame', padding="15")
        self.add_term_card.grid(row=0, column=0, sticky='ew', pady=(0, 10)) # Changed row to 1
        self.add_term_card.grid_columnconfigure(0, weight=1)

      
        # ttk.Label(self.add_term_card, text="Add New Term", style='Dialog.CardLabel.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 8))

        # Main Term Input
        ttk.Label(self.add_term_card, text="Main Term", 
                compound='left',
                style='Dialog.CardLabel.TLabel').grid(row=1, column=0, sticky='w', pady=(0, 5), padx=(0, 10))
        self.main_term_entry = tk.Entry(self.add_term_card, textvariable=self.new_main_term_var,
                                bg=self.colors['card_bg'], fg=self.colors['text'],
                                insertbackground=self.colors['text'],
                                font=('Segoe UI', 11), relief='flat', bd=0,
                                highlightbackground=self.colors.get('border', self.colors['accent']),
                                highlightthickness=1, highlightcolor=self.colors['accent'])
        self.main_term_entry.grid(row=1, column=1, sticky='ew', pady=(0, 15))

        # Synonyms Input
        ttk.Label(self.add_term_card, text="Synonyms (comma-separated)", 
                compound='left',
                style='Dialog.CardLabel.TLabel').grid(row=2, column=0, sticky='w', pady=(0, 5), padx=(0, 10))
        self.synonyms_entry = tk.Entry(self.add_term_card, textvariable=self.new_synonyms_var,
                                bg=self.colors['card_bg'], fg=self.colors['text'],
                                insertbackground=self.colors['text'],
                                font=('Segoe UI', 11), relief='flat', bd=0,
                                highlightbackground=self.colors.get('border', self.colors['accent']),
                                highlightthickness=1, highlightcolor=self.colors['accent'])
        self.synonyms_entry.grid(row=2, column=1, sticky='ew', pady=(0, 15))

        # Configure columns
        self.add_term_card.columnconfigure(0, weight=0)
        self.add_term_card.columnconfigure(1, weight=1)

        add_term_btn = ttk.Button(self.add_term_card, text="Add/Update Term",
                                  command=self.add_user_term,
                                  image=self.icons.get('add'),
                                  compound='left',
                                  style='Dialog.Primary.TButton')
        add_term_btn.grid(row=5, column=0, sticky='w')

        # Current User Terms Card - Enhanced
        self.current_terms_card = ttk.Frame(content_frame, style='Dialog.Card.TFrame', padding="15")
        self.current_terms_card.grid(row=1, column=0, sticky='nsew', pady=(0, 0)) # Changed row to 2
        self.current_terms_card.grid_columnconfigure(0, weight=1)
        self.current_terms_card.grid_rowconfigure(1, weight=1)

        ttk.Label(self.current_terms_card, text="Current Terms", 
                 image=self.icons.get('document'), compound='left',
                 style='Dialog.CardTitle.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 12))

        # Treeview with better styling
        self.terms_tree = ttk.Treeview(self.current_terms_card, columns=("Main Term", "Synonyms"), 
                                       show="headings", style='Dialog.Modern.Treeview', height=10)
        self.terms_tree.heading("Main Term", text="Main Term")
        self.terms_tree.heading("Synonyms", text="Synonyms")
        self.terms_tree.column("Main Term", width=150)
        self.terms_tree.column("Synonyms", width=300)
        self.terms_tree.grid(row=1, column=0, sticky='nsew', pady=(0, 15), columnspan=2)

        # Scrollbar
        tree_scrollbar = ttk.Scrollbar(self.current_terms_card, orient="vertical", command=self.terms_tree.yview)
        tree_scrollbar.grid(row=1, column=2, sticky='ns', pady=(0, 15))
        self.terms_tree.configure(yscrollcommand=tree_scrollbar.set)

        # Button frame for better layout
        button_frame = ttk.Frame(self.current_terms_card, style='Dialog.Card.TFrame')
        button_frame.grid(row=2, column=0, columnspan=2, sticky='ew')
        button_frame.grid_columnconfigure(1, weight=1)

        edit_term_btn = ttk.Button(button_frame, text="Edit Selected",
                                   command=self._populate_fields_from_selection,
                                   image=self.icons.get('edit'), # Reusing document icon for edit
                                   compound='left',
                                   style='Dialog.Primary.TButton')
        edit_term_btn.pack(side='left', padx=(0, 10)) # Add some padding to the right

        remove_term_btn = ttk.Button(button_frame, text="Remove Selected",
                                     command=self.remove_user_term,
                                     image=self.icons.get('trash'),
                                     compound='left',
                                     style='Dialog.Primary.TButton')
        remove_term_btn.pack(side='left')

        # Status label
        self.status_label = ttk.Label(button_frame, text="", style='Dialog.Status.TLabel')
        self.status_label.pack(side='right', padx=(10, 0))

        self._update_status()

    def _update_status(self):
        count = len(self.dictionary_manager.get_all_user_terms())
        self.status_label.config(text=f"{count} term{'s' if count != 1 else ''} in dictionary")

    def add_user_term(self):
        main_term = self.new_main_term_var.get().strip()
        synonyms_str = self.new_synonyms_var.get().strip()

        if not main_term:
            messagebox.showwarning("Input Error", "Main Term cannot be empty.", parent=self)
            return

        synonyms = [s.strip() for s in synonyms_str.split(',') if s.strip()]
        if not synonyms:
            synonyms = [main_term]

        self.dictionary_manager.add_term(main_term, synonyms)
        self.load_user_terms_to_treeview()
        self.new_main_term_var.set("")
        self.new_synonyms_var.set("")
        self._update_status()
        messagebox.showinfo("Success", f"✓ Term '{main_term}' added/updated successfully.", parent=self)
        self.log(f"Dictionary: Added/Updated term '{main_term}' with synonyms: {', '.join(synonyms)}", 'info')

    def remove_user_term(self):
        selected_item = self.terms_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a term to remove.", parent=self)
            return

        main_term = self.terms_tree.item(selected_item, 'values')[0]
        
        if messagebox.askyesno("Confirm Removal", f"Remove '{main_term}' from dictionary?", parent=self):
            if self.dictionary_manager.remove_term(main_term):
                self.load_user_terms_to_treeview()
                self._update_status()
                messagebox.showinfo("Success", f"✓ Term '{main_term}' removed successfully.", parent=self)
                self.log(f"Dictionary: Removed term '{main_term}'", 'info')
            else:
                messagebox.showerror("Error", f"Failed to remove term '{main_term}'.", parent=self)

    def load_user_terms_to_treeview(self):
        for item in self.terms_tree.get_children():
            self.terms_tree.delete(item)

        user_terms = self.dictionary_manager.get_all_user_terms()
        for entry in user_terms:
            main_term = entry.get("main_term", "")
            synonyms = ", ".join(entry.get("synonyms", []))
            self.terms_tree.insert("", tk.END, values=(main_term, synonyms))

    def _update_colors_from_parent(self):
        """Get the current theme from parent window"""
        self.is_dark_mode = self.parent.is_dark_mode
        self.colors = self.themes['dark' if self.is_dark_mode else 'light']

    def _load_user_terms_path_from_config(self):
        """Loads the user medical terms file path from config.json."""
        if self.config_file_path.exists():
            try:
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("user_medical_terms_path", "")
            except json.JSONDecodeError:
                self.log("Error: Could not decode config.json. File might be corrupted.", 'error')
            except Exception as e:
                self.log(f"An unexpected error occurred while loading config: {e}", 'error')
        return ""
