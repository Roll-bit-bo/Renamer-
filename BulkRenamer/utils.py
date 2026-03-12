"""
Utilities Module.
Contains helper classes and functions for logging and UI enhancements.
"""
import tkinter as tk
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

import config

def setup_logging():
    """
    Sets up structured logging to a rotating file.
    Keeps 3 backups of 1MB each.
    """
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler = RotatingFileHandler(config.LOG_FILE, maxBytes=1024*1024, backupCount=3)
    handler.setFormatter(log_formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

class ToolTip:
    """A class to display a tooltip popup when hovering over a widget."""
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tooltip_window: Optional[tk.Toplevel] = None
        self.id: Optional[str] = None
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def schedule_tooltip(self, event=None):
        """Waits 500ms before showing the tooltip."""
        self.id = self.widget.after(500, self.show_tooltip)

    def show_tooltip(self, event=None):
        """Creates and displays the tooltip window."""
        if self.tooltip_window or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        except Exception:
            # Widget might have been destroyed before tooltip could be shown
            return
            
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw, text=self.text, background="#333333", foreground="#ffffff",
            relief="solid", borderwidth=1, font=("Segoe UI", 9, "normal"),
            padx=8, pady=4
        )
        label.pack()

    def hide_tooltip(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None