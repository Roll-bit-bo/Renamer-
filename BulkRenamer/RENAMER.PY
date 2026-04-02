"""
Main Entry Point for Core Renamer.
This script initializes the logging system and launches the main GUI application.
"""
import tkinter as tk 
import logging
from utils import setup_logging
from gui import BulkRenamerGUI

if __name__ == "__main__":
    # 1. Setup logging configuration (file rotation, formatting)
    setup_logging()
    
    # 2. Initialize the main Tkinter root window
    root = tk.Tk()
    
    # 3. Start the application logic
    app = BulkRenamerGUI(root)
    
    # 4. Enter the main event loop (keeps app running)
    root.mainloop()
