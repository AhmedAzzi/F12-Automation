# main.py
from gui.document_processor_gui import DocumentProcessorGUI
import tkinter as tk

def main():
    root = tk.Tk()
    app = DocumentProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()