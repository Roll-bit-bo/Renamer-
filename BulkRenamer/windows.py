"""
Secondary Windows.
Defines the Toplevel windows for File Preview and History Management.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import logging
from typing import List, Tuple, Dict, Callable

class PreviewWindow(tk.Toplevel):
    """A Toplevel window to show the preview of file renames."""
    def __init__(self, parent, preview_data: List[Tuple[str, str]], tr_func: Callable):
        super().__init__(parent)
        self.tr = tr_func
        self.title(self.tr("preview_title", len(preview_data)))
        self.preview_data = preview_data
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()

        # Toolbar for actions (Export, etc)
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        self.tree = ttk.Treeview(self, columns=("old", "new"), show="headings")

        ttk.Button(toolbar, text=self.tr("export_csv"), command=self._export_csv).pack(side=tk.RIGHT)
        ttk.Label(toolbar, text=self.tr("matching_files", len(preview_data))).pack(side=tk.LEFT)

        self.tree.heading("old", text=self.tr("current_name"))
        self.tree.heading("new", text=self.tr("new_name"))
        self.tree.column("old", width=280)
        self.tree.column("new", width=280)

        # Populate the tree
        for old, new in preview_data:
            self.tree.insert("", tk.END, values=(old, new))

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _export_csv(self):
        """Handles exporting the preview data to a CSV file."""
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filepath:
            try:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([self.tr("current_name"), self.tr("new_name")])
                    writer.writerows(self.preview_data)
                messagebox.showinfo(self.tr("success"), self.tr("export_success"), parent=self)
                logging.info(f"Preview exported to {filepath}")
            except Exception as e:
                messagebox.showerror(self.tr("error"), self.tr("export_fail", e), parent=self)
                logging.error(f"Failed to export preview CSV: {e}")

class HistoryWindow(tk.Toplevel):
    """A Toplevel window to show rename history and allow undo."""
    def __init__(self, parent, history: List[Dict], undo_callback: Callable, clear_callback: Callable, tr_func: Callable):
        super().__init__(parent)
        self.history = history
        self.undo_callback = undo_callback
        self.clear_callback = clear_callback
        self.tr = tr_func
        self.session_map = {}

        self.title(self.tr("history_title"))
        self.geometry("700x450")
        self.transient(parent)
        self.grab_set()
        
        # Header
        ttk.Label(self, text=self.tr("select_session"), padding=10).pack()

        columns = ("timestamp", "folder", "count")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("timestamp", text=self.tr("time"))
        self.tree.heading("folder", text=self.tr("folder"))
        self.tree.heading("count", text=self.tr("files_renamed"))
        
        self.tree.column("timestamp", width=180)
        self.tree.column("folder", width=350)
        self.tree.column("count", width=100)
        
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Populate history tree (newest first)
        for i, session in enumerate(reversed(self.history)):
            item_id = self.tree.insert("", tk.END, values=(session.get("session", "N/A"), session.get("folder", "N/A"), len(session.get("files", []))))
            self.session_map[item_id] = session

        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)
        self.undo_btn = ttk.Button(btn_frame, text=self.tr("undo_selected"), command=self.on_undo, style="Accent.TButton")
        self.undo_btn.pack(side=tk.RIGHT)
        self.close_btn = ttk.Button(btn_frame, text=self.tr("close"), command=self.destroy)
        self.close_btn.pack(side=tk.RIGHT, padx=5)
        self.clear_btn = ttk.Button(btn_frame, text=self.tr("clear_history"), command=self.on_clear_history)
        self.clear_btn.pack(side=tk.LEFT)

    def on_undo(self):
        if not (selected := self.tree.selection()):
            return messagebox.showwarning(self.tr("warning"), "Please select a session to undo.", parent=self)
        
        session = self.session_map[selected[0]]
        if self.undo_callback(session, self):
            self.undo_btn.config(state=tk.DISABLED)
            self.clear_btn.config(state=tk.DISABLED)

    def on_clear_history(self):
        if messagebox.askyesno(self.tr("confirm_clear_title"), self.tr("confirm_clear"), parent=self):
            if self.clear_callback():
                for item in self.tree.get_children(): self.tree.delete(item)