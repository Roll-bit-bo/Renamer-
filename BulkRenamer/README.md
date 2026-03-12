# Core Renamer

A powerful, user-friendly Bulk File Renamer built with Python and Tkinter. This tool allows content creators, data managers, and power users to organize files efficiently with features like smart suggestions, live previews, and robust undo functionality.

*(Note: You can add a screenshot of the application here!)*
<!-- !Core Renamer Screenshot -->

## Features

- **Dynamic Renaming Patterns**: Use placeholders like `{original}`, `{num}`, and `{date}` to create complex naming structures (e.g., `Vacation-{date}-{num}`).
- **Smart Suggestions**: The app analyzes your files and suggests relevant names based on the folder name, common dates, and file types.
- **Live Preview**: The main file list updates in real-time as you define your renaming rules, showing you exactly what will change.
- **Session-Based Undo**: Safely revert an entire batch of renames from the History window, even after closing the app.
- **Powerful Filtering**: Isolate files by type (Images, Videos, etc.) or by text contained within the filename.
- **Multi-Language Support**: UI translated into both English and Arabic.
- **Light & Dark Modes**: Toggle between themes for your viewing comfort. The app respects system theme settings on Windows.
- **Zero Dependencies**: Runs out-of-the-box with a standard Python 3 installation. No `pip install` needed!

## How to Use

1.  **Select Folder**: Click `Browse...` to choose the folder containing files you want to rename.
2.  **Filter Files (Optional)**: Use the `File Type` dropdown or `Contains Text` field to narrow down the list of files.
3.  **Define Name**:
    -   Type a pattern into the `New Base Name` field (e.g., `Project-File-{num}`).
    -   Or, click one of the `Smart Suggestions` that appear.
4.  **Preview Changes**: The `Files List` will automatically update to show the `Current Name` and the proposed `New Name`.
5.  **Execute**: When you're happy with the preview, click `Rename Files`.
6.  **Undo (If Needed)**: Made a mistake? Go to `Tools > History / Undo`, select the operation, and click `Undo Selected Session`.

## Installation & Running

This project requires Python 3.

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Core-Renamer.git
   ```
2. Navigate to the folder:
   ```bash
   cd Core-Renamer
   ```
3. Run the application:
   ```bash
    python RENAMER.PY
   ```

## Project Structure

This project is organized to separate concerns, making it easier to understand and maintain.

```
.
├── RENAMER.PY          # Main entry point for the application.
├── gui.py              # Defines the main application window and all UI logic (Tkinter).
├── services.py         # Contains the core business logic (renaming, undo, suggestions).
├── windows.py          # Defines Toplevel windows like the Preview and History dialogs.
├── config.py           # Stores all configuration, constants, file paths, and translations.
├── utils.py            # Helper classes and functions (e.g., ToolTip, logging setup).
├── storage.py          # Handles saving and loading of JSON data (settings, history).
├── .gitignore          # Specifies files for Git to ignore (logs, user data, etc.).
└── README.md           # This file.
```

## Data and Configuration Files

The application generates a few files in its root directory to store settings and history. These are intentionally excluded from Git via `.gitignore`.

- `app_settings.json`: Stores your UI preferences, such as the last used folder, theme (dark/light), and language. You can delete this file to reset the application to its default state.
- `rename_history.json`: A log of all past renaming operations. This file is crucial for the Undo functionality.
- `app.log`: A log file that records application events and errors, which is useful for debugging.

## Contributing

Contributions are welcome! If you have an idea for a new feature or have found a bug, please feel free to open an issue or submit a pull request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` file for more information. (You should add a LICENSE file).