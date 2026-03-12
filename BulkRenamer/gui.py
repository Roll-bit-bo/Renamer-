import tkinter as tk
import sys
import os
import subprocess
import ctypes
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import logging
import threading
import time
from datetime import datetime
from typing import Optional, List, Tuple

import config
import services
import storage
from utils import ToolTip
from windows import PreviewWindow, HistoryWindow

class BulkRenamerGUI:
    """
    Main Application Class.
    Handles the UI layout, event binding, and interaction between the user and the services.
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.root.geometry("1024x800")
        self.root.minsize(800, 600)
        
        # Initialize Theme Styling
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Application State
        self.folder_path: Optional[Path] = None
        self.settings = storage.load_json_file(config.SETTINGS_FILE)
        self.is_dark_mode = self.settings.get("dark_mode", False)
        self.language = self.settings.get("language", "en")
        self.operation_in_progress = False
        self.current_files: List[str] = []
        
        # Set title after language is loaded to ensure it's translated
        self.root.title(f"{self.tr('app_title')} v{config.APP_VERSION}")

        # Set the window icon
        try:
            if os.path.exists("app_icon.ico"):
                self.root.iconbitmap("app_icon.ico")
        except Exception as e:
            logging.warning(f"Could not set window icon: {e}")

        # Build UI Components
        self._create_menu()
        self._create_widgets()
        self.restore_settings()
        self.apply_theme()
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        logging.info("Application initialized successfully.")
        
    def tr(self, key, *args):
        """Helper method to translate a key to the current language."""
        text = config.TRANSLATIONS.get(self.language, {}).get(key, key)
        if args:
            return text.format(*args)
        return text

    def _create_menu(self):
        """Creates the top menu bar (File, Edit, Tools, Help)."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=self.tr("select_folder"), command=self.select_folder)
        file_menu.add_separator()
        file_menu.add_command(label=self.tr("exit"), command=self.on_close)
        menubar.add_cascade(label=self.tr("file"), menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label=self.tr("reset_fields"), command=self._reset_fields)
        menubar.add_cascade(label=self.tr("edit"), menu=edit_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label=self.tr("history_undo"), command=self.view_history)
        menubar.add_cascade(label=self.tr("tools"), menu=tools_menu)

        # Language Menu
        lang_menu = tk.Menu(menubar, tearoff=0)
        lang_menu.add_command(label=self.tr("english"), command=lambda: self.change_language("en"))
        lang_menu.add_command(label=self.tr("arabic"), command=lambda: self.change_language("ar"))
        menubar.add_cascade(label=self.tr("language"), menu=lang_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=self.tr("help_guide"), command=self._show_guide)
        menubar.add_cascade(label=self.tr("help"), menu=help_menu)

    def _create_widgets(self):
        """Constructs the main window layout."""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Header Section ---
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.title_label = ttk.Label(header_frame, text=self.tr("app_title"), font=("Segoe UI", 24, "bold"))
        self.title_label.pack(side=tk.LEFT)
        self.theme_btn = ttk.Button(header_frame, text=self.tr("toggle_theme"), command=self.toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT)

        # --- Folder Selection ---
        folder_frame = ttk.LabelFrame(main_frame, text=self.tr("target_folder"), padding="10")
        folder_frame.pack(fill=tk.X, pady=5)
        
        self.folder_label = ttk.Label(folder_frame, text=self.tr("no_folder"), foreground="gray")
        self.folder_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.browse_btn = ttk.Button(folder_frame, text=self.tr("browse"), command=self.select_folder)
        self.browse_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # --- Filters Section ---
        filter_frame = ttk.LabelFrame(main_frame, text=self.tr("filters"), padding="10")
        filter_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(filter_frame, text=self.tr("file_type")).grid(row=0, column=0, sticky="w", pady=5)
        file_types = ["All Files"] + sorted(config.FILE_TYPE_EXTENSIONS.keys())
        self.type_combo = ttk.Combobox(filter_frame, values=file_types, state="readonly")
        self.type_combo.current(0)
        self.type_combo.grid(row=0, column=1, sticky="ew", padx=5)        
        self.type_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Label(filter_frame, text=self.tr("contains_text")).grid(row=0, column=2, sticky="w", pady=5, padx=(10,0))
        self.contains_entry = ttk.Entry(filter_frame)
        self.contains_entry.grid(row=0, column=3, sticky="ew", padx=5)
        self.contains_entry.bind("<KeyRelease>", self._on_filter_change)
        ToolTip(self.contains_entry, self.tr("tooltip_contains"))
        
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)

        # --- File List Frame (Live Preview) ---
        list_frame = ttk.LabelFrame(main_frame, text=self.tr("files_list"), padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ("current", "new")
        self.file_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.file_tree.heading("current", text=self.tr("current_name"))
        self.file_tree.heading("new", text=self.tr("new_name"))
        self.file_tree.column("current", width=200)
        self.file_tree.column("new", width=200)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_tree.bind("<Double-1>", self.on_file_double_click)

        # --- Smart Suggestions Frame (Initially hidden) ---
        self.suggestion_frame = ttk.LabelFrame(main_frame, text=self.tr("smart_suggestions"), padding="10")
        
        # --- Renaming Rules Section ---
        self.rules_frame = ttk.LabelFrame(main_frame, text=self.tr("renaming_rules"), padding="10")
        self.rules_frame.pack(fill=tk.X, pady=10)

        ttk.Label(self.rules_frame, text=self.tr("new_base_name")).grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.base_entry = ttk.Entry(self.rules_frame)
        self.base_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.base_entry.bind("<KeyRelease>", self._on_rule_change)
        ToolTip(self.base_entry, self.tr("tooltip_base"))

        ttk.Label(self.rules_frame, text=self.tr("start_number")).grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.start_num_entry = ttk.Entry(self.rules_frame)
        self.start_num_entry.insert(0, "1")
        self.start_num_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.start_num_entry.bind("<KeyRelease>", self._on_rule_change)
        ToolTip(self.start_num_entry, self.tr("tooltip_start"))
        
        self.rules_frame.columnconfigure(1, weight=1)

        # --- Action Buttons ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        self.preview_btn = ttk.Button(btn_frame, text=self.tr("preview"), command=self.preview_rename)
        self.preview_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.rename_btn = ttk.Button(btn_frame, text=self.tr("rename_files"), command=self.rename_files, style="Accent.TButton")
        self.rename_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=5)
        self.history_btn = ttk.Button(action_frame, text=self.tr("history_undo"), command=self.view_history)
        self.history_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.reset_btn = ttk.Button(action_frame, text=self.tr("reset_fields"), command=self._reset_fields)
        self.reset_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # --- Status Bar ---
        status_frame = ttk.Frame(main_frame, padding=(0, 10))
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(status_frame, text=self.tr("ready"), anchor=tk.W)
        self.status_label.pack(fill=tk.X, expand=True)
        self.progress_bar = ttk.Progressbar(status_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(fill=tk.X, expand=True, pady=(5,0))

    def _on_filter_change(self, event=None):
        """Called when filters (type, contains) change."""
        if event and event.widget == self.type_combo:
            self._suggest_base_name()
        self.load_files_list()

    def _on_rule_change(self, event=None):
        """Called when renaming rules (base name, start num) change."""
        self.update_preview_names()

    def load_files_list(self):
        """Scans the folder for files matching filters and updates the list."""
        if not self.folder_path: return
        
        file_type = self.type_combo.get()
        contains_filter = self.contains_entry.get()
        
        files, error = services.get_target_files(self.folder_path, file_type, contains_filter)
        if error:
            return # Silently fail on filter errors during typing

        self.current_files = files
        self.update_preview_names()

    def update_preview_names(self):
        """Updates the 'New Name' column in the file list."""
        # Clear current items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
        base_name = self.base_entry.get().strip()
        try:
            start_num = int(self.start_num_entry.get())
        except ValueError:
            start_num = 1
            
        counter = start_num
        for f in self.current_files:
            if base_name:
                new_name = services.generate_new_name(base_name, counter, f)
            else:
                new_name = "---"
            
            self.file_tree.insert("", tk.END, values=(f, new_name))
            counter += 1

    def _suggest_base_name(self, event=None):
        """Updates the base name entry based on the selected file type."""
        file_type = self.type_combo.get()
        suggestions = {
            "Images": "IMG",
            "Videos": "CLIP",
            "Documents": "DOC",
            "Audio": "AUDIO",
            "Archives": "BACKUP",
            "Projects": "PROJ"
        }
        new_name = suggestions.get(file_type, "FILE")
        self.base_entry.delete(0, tk.END)
        self.base_entry.insert(0, new_name)

    def save_settings(self):
        """Saves current UI state to JSON file for next launch."""
        settings = {
            "dark_mode": self.is_dark_mode,
            "language": self.language,
            "last_folder": str(self.folder_path) if self.folder_path else "",
            "file_type": self.type_combo.get(),
            "contains_text": self.contains_entry.get(),
            "base_name": self.base_entry.get(),
            "start_num": self.start_num_entry.get(),
            "first_run": False
        }
        storage.save_json_file(config.SETTINGS_FILE, settings)

    def restore_settings(self):
        """Loads UI state from JSON file."""
        last_folder_str = self.settings.get("last_folder")
        if last_folder_str:
            last_folder_path = Path(last_folder_str)
            if last_folder_path.is_dir():
                self.folder_path = last_folder_path
                self.folder_label.config(text=str(self.folder_path))
        
        self.type_combo.set(self.settings.get("file_type", "All Files"))
        self.contains_entry.insert(0, self.settings.get("contains_text", ""))
        self.base_entry.insert(0, self.settings.get("base_name", ""))
        self.start_num_entry.delete(0, tk.END)
        self.start_num_entry.insert(0, self.settings.get("start_num", "1"))
        logging.info("Settings restored.")

    def on_close(self):
        logging.info("Application closing.")
        self.save_settings()
        self.root.destroy()

    def change_language(self, lang):
        if self.language == lang: return
        self.language = lang
        self.save_settings()
        
        # Reload UI
        for widget in self.root.winfo_children():
            widget.destroy()
        self._create_menu()
        self._create_widgets()
        self.restore_settings()
        self.apply_theme()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        logging.info(f"Theme toggled to {'dark' if self.is_dark_mode else 'light'}.")

    def apply_theme(self):
        """Applies colors for Light or Dark mode to all widgets."""
        # Google Material Design Colors
        bg_color = "#202124" if self.is_dark_mode else "#ffffff"
        fg_color = "#e8eaed" if self.is_dark_mode else "#202124"
        entry_bg = "#303134" if self.is_dark_mode else "#f1f3f4"
        btn_bg = "#303134" if self.is_dark_mode else "#f1f3f4"
        # Google Blue Accent (#1a73e8)
        accent_bg = "#1a73e8"
        
        self.style.configure(".", background=bg_color, foreground=fg_color)
        self.style.configure("TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("TButton", background=btn_bg, foreground=fg_color)
        self.style.map("TButton", background=[("active", "#555555" if self.is_dark_mode else "#d0d0d0")])
        self.style.configure("Accent.TButton", background=accent_bg, foreground="#ffffff")
        self.style.map("Accent.TButton", background=[("active", "#005a9e")])
        self.style.configure("TLabelframe", background=bg_color, foreground=fg_color)
        self.style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)
        self.style.configure("TEntry", fieldbackground=entry_bg, foreground=fg_color)
        self.style.configure("Treeview", background=entry_bg, foreground=fg_color, fieldbackground=entry_bg)
        self.style.map("Treeview", background=[("selected", accent_bg)], foreground=[("selected", "white")])
        self.style.configure("TCombobox", fieldbackground=entry_bg, foreground=fg_color)
        
        self.root.configure(background=bg_color)
        self.theme_btn.config(text=self.tr("light_mode") if self.is_dark_mode else self.tr("dark_mode"))
        
        if self.folder_path:
            self.folder_label.config(foreground=fg_color)
            
        # Apply Dark Mode to Windows Title Bar (Windows 10/11 specific hack)
        if sys.platform == "win32":
            self.root.update_idletasks()
            try:
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                value = 1 if self.is_dark_mode else 0
                # Try attribute 20 (Windows 11 / 10 20H1+)
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(value)), 4) != 0:
                    # Fallback to attribute 19 (Windows 10 1903-1909)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(ctypes.c_int(value)), 4)
            except Exception as e:
                logging.warning(f"Failed to set title bar color: {e}")

    def _set_ui_state(self, enabled: bool):
        """Enables or Disables UI elements during processing."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.preview_btn.config(state=state)
        self.rename_btn.config(state=state)
        self.history_btn.config(state=state)
        self.browse_btn.config(state=state)
        self.reset_btn.config(state=state)
        
        menubar: tk.Menu = self.root.nametowidget(self.root['menu'])
        menubar.entryconfig("File", state=state)
        menubar.entryconfig(self.tr("file"), state=state)
        menubar.entryconfig("Edit", state=state)
        menubar.entryconfig(self.tr("edit"), state=state)
        menubar.entryconfig("Tools", state=state)
        menubar.entryconfig(self.tr("tools"), state=state)

        self.operation_in_progress = not enabled

    def select_folder(self):
        if self.operation_in_progress: return
        folder_str = filedialog.askdirectory(initialdir=self.folder_path or Path.home())
        if folder_str:
            self.folder_path = Path(folder_str)
            fg_color = "#ffffff" if self.is_dark_mode else "black"
            self.folder_label.config(text=str(self.folder_path), foreground=fg_color)
            logging.info(f"Selected folder: {self.folder_path}")
            self.run_smart_suggestions()
            self.load_files_list()
        else:
            self.folder_label.config(text=self.tr("no_folder"), foreground="gray")

    def _get_files_and_validate(self):
        """Helper to validate inputs and get target files list."""
        if not self.folder_path or not self.folder_path.is_dir():
            messagebox.showerror(self.tr("error"), self.tr("select_folder_first"))
            return None, None
            
        base_name = self.base_entry.get().strip()
        if not base_name:
            messagebox.showerror(self.tr("error"), self.tr("enter_base_name"))
            return None, None
        
        file_type = self.type_combo.get()
        contains_filter = self.contains_entry.get()
        
        files, error = services.get_target_files(self.folder_path, file_type, contains_filter)
        if error:
            messagebox.showerror(self.tr("error"), error)
            return None, None
        
        return files, base_name

    def preview_rename(self):
        """Initiates the preview generation in a separate thread."""
        if self.operation_in_progress: return
        files, base_name = self._get_files_and_validate()
        if files is None:
            return

        self._set_ui_state(False)
        self.status_label.config(text=self.tr("generating_preview"))
        self.progress_bar.start(10)

        thread = threading.Thread(target=self._preview_worker, args=(files, base_name), daemon=True)
        thread.start()

    def _preview_worker(self, files: List[str], base_name: str):
        start_num = 1
        try:
            start_num = int(self.start_num_entry.get())
        except ValueError:
            pass

        preview_data = []
        counter = start_num
        for f in files:
            new_name = services.generate_new_name(base_name, counter, f)
            preview_data.append((f, new_name))
            counter += 1
        
        self.root.after(0, self._show_preview_window, preview_data)

    def _show_preview_window(self, preview_data: List[Tuple[str, str]]):
        self.progress_bar.stop()
        self.status_label.config(text=self.tr("preview_generated"))
        self._set_ui_state(True)

        if not preview_data:
            messagebox.showinfo(self.tr("info"), self.tr("no_files_match"))
            return
        
        PreviewWindow(self.root, preview_data, self.tr)

    def rename_files(self):
        """Initiates the actual rename process in a separate thread."""
        if self.operation_in_progress: return
        files, base_name = self._get_files_and_validate()
        if files is None: return

        if not files:
            messagebox.showinfo(self.tr("info"), self.tr("no_files_rename"))
            return

        if not messagebox.askyesno(self.tr("confirm_rename_title"), self.tr("confirm_rename", len(files), self.folder_path.name, base_name)):
            return

        start_num = 1
        try: start_num = int(self.start_num_entry.get())
        except ValueError: pass

        self._set_ui_state(False)
        self.status_label.config(text=self.tr("renaming_progress"))
        self.progress_bar.config(value=0, maximum=len(files))

        thread = threading.Thread(target=self._rename_files_worker, args=(files, base_name, start_num), daemon=True)
        thread.start()

    def _rename_files_worker(self, files: List[str], base_name: str, start_num: int):
        start_time = time.perf_counter()
        
        session_history, errors = services.perform_rename(
            self.folder_path, files, base_name, start_num,
            lambda c, t, f: self.root.after(0, self._update_progress, c, t, f)
        )

        # Save to history file
        if session_history:
            history_data = storage.load_json_file(config.HISTORY_FILE)
            if not isinstance(history_data, list): history_data = []
            
            history_data.append({
                "session": datetime.now().isoformat(),
                "folder": str(self.folder_path),
                "files": session_history
            })
            storage.save_json_file(config.HISTORY_FILE, history_data)

        duration = time.perf_counter() - start_time
        self.root.after(0, self._on_rename_complete, session_history, errors, duration)

    def _update_progress(self, current: int, total: int, filename: str):
        """Callback to update progress bar from the worker thread."""
        if self.operation_in_progress:
            self.progress_bar['value'] = current
            self.status_label.config(text=self.tr("processing", current, total, filename))

    def _on_rename_complete(self, session_history: List, errors: List, duration: float):
        """Called when renaming is finished to reset UI and show results."""
        self.progress_bar['value'] = 0
        self.status_label.config(text=self.tr("complete", len(session_history), duration))
        self._set_ui_state(True)
        self.load_files_list() # Refresh list to show new names
        
        # Play a system sound to notify/remind the user the task is done
        self.root.bell()

        if errors:
            error_msg = "\n".join(errors[:10]) + (f"\n...and {len(errors)-10} more." if len(errors) > 10 else "")
            messagebox.showwarning(self.tr("completed_errors"), self.tr("rename_incomplete", len(session_history), len(errors)) + f"\n{error_msg}")
        else:
            messagebox.showinfo(self.tr("success"), self.tr("complete", len(session_history), duration))
        logging.info(f"Rename complete. {len(session_history)} files renamed. {len(errors)} errors. Duration: {duration:.2f}s.")

    def perform_undo(self, session: dict, history_window: tk.Toplevel) -> bool:
        """Starts the undo process in a separate thread."""
        if not messagebox.askyesno(self.tr("confirm_undo_title"), self.tr("confirm_undo", len(session['files']), session['session'])):
            return False
        
        thread = threading.Thread(target=self._undo_worker, args=(session, history_window), daemon=True)
        thread.start()
        return True

    def _undo_worker(self, session: dict, history_window: tk.Toplevel):
        files_undone, errors = services.perform_undo(session)

        current_history = storage.load_json_file(config.HISTORY_FILE)
        if isinstance(current_history, list):
            current_history = [s for s in current_history if s.get('session') != session.get('session')]
            storage.save_json_file(config.HISTORY_FILE, current_history)

        self.root.after(0, self._on_undo_complete, files_undone, errors, history_window)

    def _on_undo_complete(self, files_undone: int, errors: List, history_window: tk.Toplevel):
        if errors:
            messagebox.showwarning(self.tr("undo_incomplete_title"), self.tr("undo_incomplete", files_undone, len(errors)))
        else:
            messagebox.showinfo(self.tr("undo_success_title"), self.tr("undo_successful", files_undone))
        logging.info(f"Undo complete. {files_undone} files restored. {len(errors)} errors.")
        self.load_files_list() # Refresh list
            
        if history_window.winfo_exists():
            history_window.destroy()
            self.view_history()

    def view_history(self):
        """Opens the History Window."""
        if self.operation_in_progress: return
        history = storage.load_json_file(config.HISTORY_FILE)
        
        if not isinstance(history, list) or not history:
            messagebox.showinfo(self.tr("info"), self.tr("no_history"))
            return

        HistoryWindow(self.root, history, self.perform_undo, self.clear_history, self.tr)

    def clear_history(self) -> bool:
        if storage.save_json_file(config.HISTORY_FILE, []):
            messagebox.showinfo(self.tr("success"), self.tr("history_cleared"))
            logging.info("History cleared by user.")
            return True
        else:
            messagebox.showerror(self.tr("error"), "Could not clear history file.")
            return False

    def _reset_fields(self):
        """Clears all input fields and resets app state."""
        if self.operation_in_progress: return
        self.contains_entry.delete(0, tk.END)
        self.base_entry.delete(0, tk.END)
        self.start_num_entry.delete(0, tk.END)
        self.start_num_entry.insert(0, "1")
        self.type_combo.current(0)
        self.status_label.config(text=self.tr("ready"))
        
        # Clear suggestions on reset
        for widget in self.suggestion_frame.winfo_children():
            widget.destroy()
        self.suggestion_frame.pack_forget()
        self.load_files_list()
        
        logging.info("Input fields have been reset.")

    def _show_guide(self):
        """Shows a simple quick start guide."""
        # Create a custom Toplevel window for the guide
        guide_win = tk.Toplevel(self.root)
        guide_win.title(self.tr("help_guide"))
        guide_win.geometry("800x600")
        guide_win.transient(self.root)
        guide_win.grab_set()

        frame = ttk.Frame(guide_win, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(frame, text=self.tr("help_guide"), font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        # Guide Text Area
        text_widget = tk.Text(frame, wrap=tk.WORD, height=15, font=("Segoe UI", 11), relief=tk.FLAT)
        # Simple color matching for dark/light mode
        bg_color = "#303134" if self.is_dark_mode else "#f1f3f4"
        fg_color = "#e8eaed" if self.is_dark_mode else "#202124"
        text_widget.config(bg=bg_color, fg=fg_color, padx=10, pady=10)
        text_widget.insert(tk.END, self.tr("guide_text", config.APP_NAME, config.APP_VERSION))
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True, pady=10)

        ttk.Button(frame, text=self.tr("close"), command=guide_win.destroy).pack(fill=tk.X)

    def run_smart_suggestions(self):
        """Starts the background thread to generate naming suggestions."""
        if not self.folder_path: return
        
        # Clear old suggestions immediately
        for widget in self.suggestion_frame.winfo_children():
            widget.destroy()
        self.suggestion_frame.pack_forget()

        threading.Thread(target=self._suggestion_worker, daemon=True).start()

    def _suggestion_worker(self):
        """Background worker to analyze folder content."""
        suggestions = services.generate_smart_suggestions(self.folder_path)
        self.root.after(0, self._display_suggestions, suggestions)

    def _display_suggestions(self, suggestions: List[dict]):
        if not suggestions:
            return

        self.suggestion_frame.pack(fill=tk.X, pady=5, before=self.rules_frame)
        
        for s in suggestions:
            label_text = f"{self.tr(s['label'])}: {s['value']}"
            btn = ttk.Button(self.suggestion_frame, text=label_text, 
                             command=lambda v=s['value']: self.apply_suggestion(v))
            btn.pack(side=tk.LEFT, padx=5, pady=5)
            ToolTip(btn, self.tr("suggestion_reason", s['reason']))

    def apply_suggestion(self, value: str):
        """Called when a suggestion button is clicked."""
        self.base_entry.delete(0, tk.END)
        self.base_entry.insert(0, value)
        self.start_num_entry.delete(0, tk.END)
        self.start_num_entry.insert(0, "1")
        
        # Update preview and force UI refresh so user sees the change before confirmation
        self.update_preview_names()
        self.root.update_idletasks()
        
        # Immediately trigger the rename flow (which asks for confirmation)
        self.rename_files()

    def on_file_double_click(self, event):
        """Opens the selected file in the default OS application."""
        item_id = self.file_tree.selection()
        if not item_id: return
        
        file_name = self.file_tree.item(item_id[0])['values'][0]
        file_path = self.folder_path / file_name
        
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", str(file_path)])
            else:
                subprocess.call(["xdg-open", str(file_path)])
        except Exception as e:
            logging.error(f"Failed to open file: {e}")