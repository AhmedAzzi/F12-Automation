# features/dictionary/presentation/dictionary_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageTk

from shared.utils.logger import logger
from shared.config.theme import THEMES

class DictionaryDialog(tk.Toplevel):
    """UI for managing user dictionaries, decoupled from state."""

    def __init__(self, parent, dictionary_service, is_dark_mode, icons_dir: Path):
        super().__init__(parent)
        self.parent = parent
        self.dictionary_service = dictionary_service
        self.is_dark_mode = is_dark_mode
        self.icons_dir = icons_dir

        self.title("Manage User Dictionary")
        self.geometry("700x800")
        self.resizable(True, True)
        self.minsize(600, 700)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.new_main_term_var = tk.StringVar()
        self.new_synonyms_var = tk.StringVar()
        self.colors = THEMES['dark' if self.is_dark_mode else 'light']

        self.configure(bg=self.colors['bg'])

        self.setup_styles()
        self.load_icons()
        self.create_widgets()
        self.load_user_terms_to_treeview()
        
        self.main_term_entry.bind('<FocusIn>', self._on_entry_focus)
        self.main_term_entry.bind('<FocusOut>', self._on_entry_blur)
        self.synonyms_entry.bind('<FocusIn>', self._on_entry_focus)
        self.synonyms_entry.bind('<FocusOut>', self._on_entry_blur)

    def _on_entry_focus(self, event):
        event.widget.config(highlightthickness=2)

    def _on_entry_blur(self, event):
        event.widget.config(highlightthickness=1)

    def load_icons(self):
        self.icons = {}
        icon_files = {
            'document': 'document.png',
            'trash': 'trash.png',
            'dictionary': 'dictionary.png',
            'add': 'add.png',
            'edit': 'edit.png'
        }
        for key, filename in icon_files.items():
            try:
                icon_path = self.icons_dir / filename
                if icon_path.exists():
                    img_pil = Image.open(icon_path)
                    size = (30, 30) if key == 'dictionary' else (20, 20)
                    img_pil = img_pil.resize(size, Image.LANCZOS)
                    self.icons[key] = ImageTk.PhotoImage(img_pil)
                else:
                    self.icons[key] = None
            except Exception as e:
                logger.log(f"Config Error: Could not load icon {filename}: {e}", 'error')
                self.icons[key] = None

    def setup_styles(self):
        style = ttk.Style(self)
        bg = self.colors['bg']
        card_bg = self.colors['card_bg']
        hover = self.colors['card_hover']
        accent = self.colors['accent']
        text = self.colors['text']
        text_secondary = self.colors['text_secondary']

        style.configure('Dialog.Modern.TFrame', background=bg)
        style.configure('Dialog.Card.TFrame', background=card_bg, relief='flat')
        style.configure('Dialog.Title.TLabel', background=bg, foreground=text, font=('Segoe UI', 20, 'bold'))
        style.configure('Dialog.CardTitle.TLabel', background=card_bg, foreground=text, font=('Segoe UI', 12, 'bold'))
        style.configure('Dialog.CardLabel.TLabel', background=card_bg, foreground=text_secondary, font=('Segoe UI', 9))
        style.configure('Dialog.Status.TLabel', background=card_bg, foreground=text_secondary, font=('Segoe UI', 9, 'italic'))
        
        style.configure('Dialog.Primary.TButton', background=card_bg, foreground=text, borderwidth=1, relief='flat', font=('Segoe UI', 9), padding=(8, 6))
        style.map('Dialog.Primary.TButton', background=[('active', hover)], foreground=[('active', text)])

        style.configure('Dialog.Modern.Treeview.Heading', background=card_bg, foreground=text_secondary, font=('Segoe UI', 10, 'bold'), borderwidth=0)
        style.configure('Dialog.Modern.Treeview', background=card_bg, foreground=text, fieldbackground=card_bg, font=('Segoe UI', 10), borderwidth=0, rowheight=28)
        style.map('Dialog.Modern.Treeview', background=[('selected', accent)], foreground=[('selected', 'white')])
        style.layout("Dialog.Modern.Treeview", [('Dialog.Modern.Treeview.treearea', {'sticky': 'nswe'})])

    def create_widgets(self):
        self.main_frame = ttk.Frame(self, style='Dialog.Modern.TFrame', padding="10")
        self.main_frame.grid(row=0, column=0, sticky='nsew')
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        header_frame = ttk.Frame(self.main_frame, style='Dialog.Modern.TFrame')
        header_frame.grid(row=0, column=0, sticky='ew')
        ttk.Label(header_frame, text="Dictionary Manager", image=self.icons.get('dictionary'), compound='left', style='Dialog.Title.TLabel').grid(row=0, column=0, sticky='w')

        self.add_term_card = ttk.Frame(self.main_frame, style='Dialog.Card.TFrame', padding="15")
        self.add_term_card.grid(row=1, column=0, sticky='ew', pady=(10, 10))
        self.add_term_card.grid_columnconfigure(1, weight=1)

        ttk.Label(self.add_term_card, text="Main Term", style='Dialog.CardLabel.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 5), padx=(0, 10))
        self.main_term_entry = tk.Entry(self.add_term_card, textvariable=self.new_main_term_var, bg=self.colors['card_bg'], fg=self.colors['text'], insertbackground=self.colors['text'], font=('Segoe UI', 11), relief='flat', highlightbackground=self.colors.get('border', self.colors['accent']), highlightthickness=1)
        self.main_term_entry.grid(row=0, column=1, sticky='ew', pady=(0, 15))

        ttk.Label(self.add_term_card, text="Synonyms (comma-sep)", style='Dialog.CardLabel.TLabel').grid(row=1, column=0, sticky='w', pady=(0, 5), padx=(0, 10))
        self.synonyms_entry = tk.Entry(self.add_term_card, textvariable=self.new_synonyms_var, bg=self.colors['card_bg'], fg=self.colors['text'], insertbackground=self.colors['text'], font=('Segoe UI', 11), relief='flat', highlightbackground=self.colors.get('border', self.colors['accent']), highlightthickness=1)
        self.synonyms_entry.grid(row=1, column=1, sticky='ew', pady=(0, 15))

        ttk.Button(self.add_term_card, text="Add/Update Term", command=self.add_user_term, image=self.icons.get('add'), compound='left', style='Dialog.Primary.TButton').grid(row=2, column=0, sticky='w')

        self.current_terms_card = ttk.Frame(self.main_frame, style='Dialog.Card.TFrame', padding="15")
        self.current_terms_card.grid(row=2, column=0, sticky='nsew')
        self.current_terms_card.grid_columnconfigure(0, weight=1)
        self.current_terms_card.grid_rowconfigure(1, weight=1)

        ttk.Label(self.current_terms_card, text="Current Terms", image=self.icons.get('document'), compound='left', style='Dialog.CardTitle.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 12))

        self.terms_tree = ttk.Treeview(self.current_terms_card, columns=("Main Term", "Synonyms"), show="headings", style='Dialog.Modern.Treeview', height=10)
        self.terms_tree.heading("Main Term", text="Main Term")
        self.terms_tree.heading("Synonyms", text="Synonyms")
        self.terms_tree.column("Main Term", width=150)
        self.terms_tree.column("Synonyms", width=300)
        self.terms_tree.grid(row=1, column=0, sticky='nsew', pady=(0, 15))

        tree_scrollbar = ttk.Scrollbar(self.current_terms_card, orient="vertical", command=self.terms_tree.yview)
        tree_scrollbar.grid(row=1, column=1, sticky='ns', pady=(0, 15))
        self.terms_tree.configure(yscrollcommand=tree_scrollbar.set)

        btn_frame = ttk.Frame(self.current_terms_card, style='Dialog.Card.TFrame')
        btn_frame.grid(row=2, column=0, columnspan=2, sticky='ew')

        ttk.Button(btn_frame, text="Edit Selected", command=self._populate_fields, image=self.icons.get('edit'), compound='left', style='Dialog.Primary.TButton').pack(side='left', padx=(0, 10))
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_user_term, image=self.icons.get('trash'), compound='left', style='Dialog.Primary.TButton').pack(side='left')

        self.status_label = ttk.Label(btn_frame, text="", style='Dialog.Status.TLabel')
        self.status_label.pack(side='right', padx=(10, 0))

    def _update_status(self):
        count = len(self.dictionary_service.get_user_terms_raw())
        self.status_label.config(text=f"{count} term{'s' if count != 1 else ''} in dictionary")

    def _populate_fields(self):
        selected_item = self.terms_tree.focus()
        if selected_item:
            values = self.terms_tree.item(selected_item, 'values')
            self.new_main_term_var.set(values[0])
            self.new_synonyms_var.set(values[1])
        else:
            messagebox.showwarning("Error", "Please select a term.", parent=self)

    def add_user_term(self):
        mt = self.new_main_term_var.get().strip()
        syns = [s.strip() for s in self.new_synonyms_var.get().split(',') if s.strip()]
        if not mt:
            return messagebox.showwarning("Error", "Main Term empty.", parent=self)
        if not syns: syns = [mt]

        if self.dictionary_service.add_user_term(mt, syns):
            self.load_user_terms_to_treeview()
            self.new_main_term_var.set("")
            self.new_synonyms_var.set("")
            self._update_status()
            messagebox.showinfo("Success", f"Term '{mt}' saved.", parent=self)

    def remove_user_term(self):
        sel = self.terms_tree.focus()
        if not sel: return
        mt = self.terms_tree.item(sel, 'values')[0]
        if messagebox.askyesno("Confirm", f"Remove '{mt}'?", parent=self):
            if self.dictionary_service.remove_user_term(mt):
                self.load_user_terms_to_treeview()
                self._update_status()

    def load_user_terms_to_treeview(self):
        for item in self.terms_tree.get_children():
            self.terms_tree.delete(item)
        for entry in self.dictionary_service.get_user_terms_raw():
            self.terms_tree.insert("", tk.END, values=(entry.get("main_term", ""), ", ".join(entry.get("synonyms", []))))
        self._update_status()
