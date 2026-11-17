import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import shutil
from pathlib import Path

class RobocopyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced File Mover")
        self.root.geometry("850x650")
        self.root.minsize(750, 550)
        self.root.configure(bg="#f5f6f8")
        
        # Configure styles
        self.setup_styles()
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="25")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # Source selection
        ttk.Label(main_frame, text="Source:", font=("", 11, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 8))
        self.source_var = tk.StringVar()
        source_frame = ttk.Frame(main_frame)
        source_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 18))
        ttk.Entry(source_frame, textvariable=self.source_var, font=("", 10)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
        ttk.Button(source_frame, text="Browse", command=self.browse_source).pack(side=tk.RIGHT)
        
        # Destination selection
        ttk.Label(main_frame, text="Destination:", font=("", 11, "bold")).grid(
            row=2, column=0, sticky=tk.W, pady=(0, 8))
        self.dest_var = tk.StringVar()
        dest_frame = ttk.Frame(main_frame)
        dest_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 25))
        ttk.Entry(dest_frame, textvariable=self.dest_var, font=("", 10)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
        ttk.Button(dest_frame, text="Browse", command=self.browse_dest).pack(side=tk.RIGHT)
        
        # Operation buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(0, 22))
        self.copy_btn = ttk.Button(button_frame, text="COPY", command=self.copy_files, width=18)
        self.copy_btn.pack(side=tk.LEFT, padx=(0, 15))
        self.move_btn = ttk.Button(button_frame, text="CUT", command=self.move_files, width=18)
        self.move_btn.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 18))
        
        # Log display
        ttk.Label(main_frame, text="Operation Log:", font=("", 11, "bold")).grid(
            row=6, column=0, sticky=tk.W, pady=(12, 8))
        self.log_text = scrolledtext.ScrolledText(
            main_frame, 
            height=16, 
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#ffffff",
            relief="flat",
            borderwidth=1
        )
        self.log_text.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
        
        # Initialize variables
        self.is_running = False
        self.source_paths = []  # Will store multiple file/folder paths
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        bg_color = "#f5f6f8"
        btn_color = "#4a6cf7"
        btn_hover = "#3a5bf5"
        
        # Main window
        self.root.configure(bg=bg_color)
        
        # Button styles
        style.configure('TButton', 
                       font=("", 10, "bold"), 
                       padding=8,
                       background=btn_color,
                       foreground="white",
                       borderwidth=0)
        style.map('TButton',
                  background=[('pressed', btn_hover), ('active', btn_hover)],
                  foreground=[('pressed', 'white'), ('active', 'white')])
        
        # Entry styles
        style.configure('TEntry', 
                       padding=6,
                       fieldbackground="white",
                       bordercolor="#d0d0d0",
                       lightcolor="#e0e0e0",
                       darkcolor="#e0e0e0")
        
        # Progress bar style
        style.configure("TProgressbar", 
                       thickness=8,
                       background=btn_color,
                       troughcolor="#e0e0e0")
        
        # Frame style
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color)
    
    def browse_source(self):
        """Unified dialog for selecting files and/or folders"""
        # Create custom dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Files and Folders")
        dialog.geometry("500x400")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Selected items list
        selected_items = []
        listbox = tk.Listbox(dialog, selectmode=tk.EXTENDED, height=15)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def add_files():
            files = filedialog.askopenfilenames(
                title="Select Files",
                parent=dialog,
                filetypes=[("All files", "*.*")]
            )
            for file in files:
                if file not in selected_items:
                    selected_items.append(file)
                    listbox.insert(tk.END, f"📄 {os.path.basename(file)} ({file})")
            update_display()
        
        def add_folder():
            folder = filedialog.askdirectory(
                title="Select Folder",
                parent=dialog
            )
            if folder:
                if folder not in selected_items:
                    selected_items.append(folder)
                    listbox.insert(tk.END, f"📁 {os.path.basename(folder)} ({folder})")
                update_display()
        
        def remove_selected():
            selected_indices = listbox.curselection()
            for i in reversed(selected_indices):
                del selected_items[i]
                listbox.delete(i)
            update_display()
        
        def update_display():
            if len(selected_items) == 0:
                self.source_var.set("")
            elif len(selected_items) == 1:
                self.source_var.set(selected_items[0])
            else:
                self.source_var.set(f"{len(selected_items)} items selected")
        
        def confirm_selection():
            self.source_paths = selected_items.copy()
            dialog.destroy()
        
        def cancel_selection():
            dialog.destroy()
        
        # Button frame
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(btn_frame, text="Add Files", command=add_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Add Folder", command=add_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Remove", command=remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="OK", command=confirm_selection, style='Accent.TButton').pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(btn_frame, text="Cancel", command=cancel_selection).pack(side=tk.RIGHT)
        
        # Configure accent style for OK button
        style = ttk.Style()
        style.configure('Accent.TButton', background='#4CAF50', foreground='white')
        style.map('Accent.TButton', background=[('active', '#45a049')])
        
        # Initialize with current selection
        for item in self.source_paths:
            if os.path.isdir(item):
                listbox.insert(tk.END, f"📁 {os.path.basename(item)} ({item})")
            else:
                listbox.insert(tk.END, f"📄 {os.path.basename(item)} ({item})")
        selected_items.extend(self.source_paths)
        update_display()
        
        dialog.wait_window()
    
    def browse_dest(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            self.dest_var.set(path)
    
    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def validate_paths(self):
        if not self.source_paths:
            messagebox.showerror("Error", "Please select source file(s) or folder(s)")
            return False
            
        dest = self.dest_var.get().strip()
        if not dest:
            messagebox.showerror("Error", "Please specify a destination path")
            return False
            
        if not os.path.exists(dest):
            try:
                os.makedirs(dest)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create destination folder:\n{str(e)}")
                return False
                
        # Check if any source is the same as destination
        for src in self.source_paths:
            if os.path.normpath(src) == os.path.normpath(dest):
                messagebox.showerror("Error", "Source and destination cannot be the same")
                return False
                
        return True
    
    def copy_single_file(self, src, dest_dir):
        """Copy a single file with progress simulation"""
        try:
            filename = os.path.basename(src)
            dest_path = os.path.join(dest_dir, filename)
            
            # Handle filename conflicts
            counter = 1
            original_dest = dest_path
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(original_dest)
                dest_path = f"{name} ({counter}){ext}"
                counter += 1
            
            shutil.copy2(src, dest_path)
            return True, f"Copied: {filename}"
        except Exception as e:
            return False, f"Error copying {src}: {str(e)}"
    
    def move_single_file(self, src, dest_dir):
        """Move a single file"""
        try:
            filename = os.path.basename(src)
            dest_path = os.path.join(dest_dir, filename)
            
            # Handle filename conflicts
            counter = 1
            original_dest = dest_path
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(original_dest)
                dest_path = f"{name} ({counter}){ext}"
                counter += 1
            
            shutil.move(src, dest_path)
            return True, f"Moved: {filename}"
        except Exception as e:
            return False, f"Error moving {src}: {str(e)}"
    
    def copy_folder_as_container(self, src, dest_dir):
        """Copy entire folder as a container (not just contents)"""
        try:
            folder_name = os.path.basename(src)
            dest_path = os.path.join(dest_dir, folder_name)
            
            # Handle folder name conflicts
            counter = 1
            original_dest = dest_path
            while os.path.exists(dest_path):
                dest_path = f"{original_dest} ({counter})"
                counter += 1
            
            # Create destination folder structure
            os.makedirs(dest_path, exist_ok=True)
            
            # Use Robocopy to copy contents INTO the new folder
            cmd = ["robocopy", src, dest_path, "/E", "/Z", "/R:1", "/W:1", "/NP", "/NJH", "/NJS"]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Read output (we'll capture it but not display in real-time for folders)
            output, _ = process.communicate()
            rc = process.returncode
            
            if rc <= 1:
                return True, f"Copied folder: {folder_name}"
            else:
                return False, f"Error copying folder {folder_name} (Code: {rc})"
                
        except Exception as e:
            return False, f"Error copying folder {src}: {str(e)}"
    
    def move_folder_as_container(self, src, dest_dir):
        """Move entire folder as a container"""
        try:
            folder_name = os.path.basename(src)
            dest_path = os.path.join(dest_dir, folder_name)
            
            # Handle folder name conflicts
            counter = 1
            original_dest = dest_path
            while os.path.exists(dest_path):
                dest_path = f"{original_dest} ({counter})"
                counter += 1
            
            # Move the entire folder
            shutil.move(src, dest_path)
            return True, f"Moved folder: {folder_name}"
            
        except Exception as e:
            return False, f"Error moving folder {src}: {str(e)}"
    
    def run_operation(self, is_move=False):
        if not self.validate_paths():
            return
            
        dest = self.dest_var.get().strip()
        operation = "CUT" if is_move else "COPY"
        
        self.log_message(f"\n{'='*60}")
        self.log_message(f"Starting {operation} operation...")
        self.log_message(f"Destination: {dest}")
        if len(self.source_paths) == 1:
            self.log_message(f"Source: {self.source_paths[0]}")
        else:
            self.log_message(f"Sources: {len(self.source_paths)} items")
        self.log_message(f"{'='*60}\n")
        
        try:
            self.progress.start()
            self.copy_btn.config(state=tk.DISABLED)
            self.move_btn.config(state=tk.DISABLED)
            self.is_running = True
            
            success_count = 0
            error_count = 0
            
            for src in self.source_paths:
                if os.path.isdir(src):
                    # Handle folder as container
                    if is_move:
                        success, msg = self.move_folder_as_container(src, dest)
                    else:
                        success, msg = self.copy_folder_as_container(src, dest)
                    
                    self.log_message(msg)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        
                else:
                    # Handle single file
                    if is_move:
                        success, msg = self.move_single_file(src, dest)
                    else:
                        success, msg = self.copy_single_file(src, dest)
                    
                    self.log_message(msg)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
            
            # Final summary
            self.log_message(f"\n{'='*60}")
            self.log_message(f"OPERATION COMPLETE")
            self.log_message(f"Successful: {success_count} | Errors: {error_count}")
            if error_count > 0:
                self.log_message("Check log for error details")
            self.log_message(f"{'='*60}")
            
        except Exception as e:
            self.log_message(f"\nCRITICAL ERROR: {str(e)}")
            messagebox.showerror("Operation Failed", f"An unexpected error occurred:\n{str(e)}")
        finally:
            self.progress.stop()
            self.copy_btn.config(state=tk.NORMAL)
            self.move_btn.config(state=tk.NORMAL)
            self.is_running = False
    
    def copy_files(self):
        if self.is_running:
            messagebox.showwarning("Warning", "Another operation is already running!")
            return
        threading.Thread(target=self.run_operation, args=(False,), daemon=True).start()
    
    def move_files(self):
        if self.is_running:
            messagebox.showwarning("Warning", "Another operation is already running!")
            return
            
        if messagebox.askyesno(
            "Confirm Move", 
            "Moving will DELETE original files/folders after transfer!\n\n"
            "Are you sure you want to proceed?",
            icon="warning"
        ):
            threading.Thread(target=self.run_operation, args=(True,), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = RobocopyGUI(root)
    root.mainloop()