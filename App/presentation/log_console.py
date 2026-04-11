# presentation/log_console.py
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import List, Tuple

class LogConsole:
    """Manages the UI component for logging operations."""
    
    def __init__(self, parent_frame, colors, icons):
        self.parent = parent_frame
        self.colors = colors
        self.icons = icons
        
        self.log_buffer: List[Tuple[str, str]] = []
        self.log_buffer_max_size = 50
        self.all_log_entries: List[Tuple[str, str]] = []
        self.current_file_log_context: List[Tuple[str, str]] = []
        
        self.search_var = tk.StringVar()
        
        self._build_ui()

    def _build_ui(self):
        log_section = ttk.Frame(self.parent, style='Modern.TFrame')
        log_section.grid(row=3, column=0, sticky='nsew', pady=(0, 10))
        log_section.grid_rowconfigure(1, weight=1)
        log_section.grid_columnconfigure(0, weight=1)
        log_section.grid_propagate(False)
        log_section.config(height=300)
        
        log_title_frame = ttk.Frame(log_section, style='Modern.TFrame')
        log_title_frame.grid(row=0, column=0, sticky='w', pady=(0, 8))
        
        if self.icons.get('log'):
            tk.Label(log_title_frame, image=self.icons['log'], bg=self.colors['bg'], bd=0).grid(row=0, column=0, padx=(0, 5))
        
        ttk.Label(log_title_frame, text="Processing Log", style='CardTitle.TLabel').grid(row=0, column=1, sticky='w')
        
        log_card = ttk.Frame(log_section, style='Card.TFrame', padding="10")
        log_card.grid(row=1, column=0, sticky='nsew')
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_propagate(False)
        log_card.config(width=400, height=250)
        
        # Search bar
        search_bar_frame = ttk.Frame(log_card, style='Card.TFrame')
        search_bar_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        search_bar_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = tk.Entry(
            search_bar_frame, textvariable=self.search_var,
            bg=self.colors['card_bg'], fg=self.colors['text'],
            insertbackground=self.colors['text'],
            font=('Segoe UI', 10), relief='flat', bd=0,
            highlightbackground=self.colors.get('border', self.colors['accent']),
            highlightthickness=1, highlightcolor=self.colors['accent']
        )
        self.search_entry.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        self.search_entry.bind("<Return>", lambda event=None: self.search_logs())

        ttk.Button(
            search_bar_frame, text="Search", command=self.search_logs,
            style='Secondary.TButton', image=self.icons.get('search'), compound=tk.LEFT
        ).grid(row=0, column=1, sticky='e')
        
        # Notebook
        self.main_notebook = ttk.Notebook(log_card, style="Modern.TNotebook")
        self.main_notebook.grid(row=1, column=0, sticky='nsew', padx=2, pady=2)

        # Tabs
        self.all_log_text = self._create_log_tab("All")
        self.success_log_text = self._create_log_tab("Success")
        self.error_log_text = self._create_log_tab("Errors")
        
        self.apply_theme_colors(self.colors)

    def _create_log_tab(self, title: str):
        frame = tk.Frame(self.main_notebook, bg=self.colors['card_bg'])
        self.main_notebook.add(frame, text=title)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        text_widget = scrolledtext.ScrolledText(
            frame, bg=self.colors['card_bg'], fg=self.colors['text'],
            font=('Consolas', 10), relief='flat', bd=0,
            insertbackground=self.colors['text'],
            selectbackground=self.colors['accent'],
            selectforeground='white', wrap=tk.WORD,
        )
        text_widget.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
        text_widget.bind("<Key>", lambda e: "break")
        return text_widget

    def apply_theme_colors(self, colors):
        self.colors = colors
        tags = {
            'success': colors['success'],
            'warning': colors['warning'],
            'info': colors['text_secondary'],
            'error': colors['error']
        }
        for text_widget in [self.all_log_text, self.success_log_text, self.error_log_text]:
            text_widget.config(
                bg=colors['card_bg'], fg=colors['text'],
                insertbackground=colors['text'], selectbackground=colors['accent']
            )
            for tag_name, color in tags.items():
                text_widget.tag_config(tag_name, foreground=color)
        
        self.search_entry.config(
            bg=colors['card_bg'], fg=colors['text'], insertbackground=colors['text'],
            highlightbackground=colors.get('border', colors['accent'])
        )

    def append_log(self, message: str, tag: str = 'info'):
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
        elif tag in ('error', 'summary_error'):
            if "❌ Errors:" in message:
                self.error_log_text.insert(tk.END, message + '\n', tag)
            else:
                for ctx_msg, ctx_tag in self.current_file_log_context:
                    self.error_log_text.insert(tk.END, ctx_msg + '\n', ctx_tag)
                self.error_log_text.see(tk.END)
            self.current_file_log_context = []
        elif tag == 'warning' and ("No confident match" in message or "No match found" in message):
            for ctx_msg, ctx_tag in self.current_file_log_context:
                self.error_log_text.insert(tk.END, ctx_msg + '\n', ctx_tag)
            self.error_log_text.see(tk.END)
            self.current_file_log_context = []

    def clear(self):
        self.all_log_text.delete(1.0, tk.END)
        self.success_log_text.delete(1.0, tk.END)
        self.error_log_text.delete(1.0, tk.END)
        self.log_buffer.clear()
        self.current_file_log_context.clear()
        self.append_log("Log cleared.", 'info')

    def search_logs(self):
        search_term = self.search_var.get().lower()
        self.all_log_text.delete("1.0", tk.END)
        
        if not search_term:
            for msg, tag in self.all_log_entries:
                self.all_log_text.insert(tk.END, msg + '\n', tag)
        else:
            for msg, tag in self.all_log_entries:
                if search_term in msg.lower():
                    self.all_log_text.insert(tk.END, msg + '\n', tag)
        
        self.all_log_text.see(tk.END)
