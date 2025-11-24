# Photo Metadata Viewer & Searcher

## 📌 Overview
This application lets you:
- Browse all images in a selected folder.
- View embedded metadata comments (EXIF/XMP).
- Edit and save comments back into image metadata.
- Search images by these metadata comments.

The goal is to provide a simple desktop tool to organize photos using textual notes stored directly inside each file.

---

## ✨ Features
- **Folder Image Browser** – displays thumbnails or list of images from a chosen directory.
- **Metadata Comment Viewer** – reads `UserComment` or `ImageDescription` (EXIF) or XMP description fields.
- **Comment Editor** – allows modifying and saving comments back into image metadata.
- **Search Functionality** – searches images in the folder based on embedded metadata comments.
- **Supports JPEG, PNG (XMP), WEBP, TIFF**.

---

## 🏗 Technology Stack
- **Python 3.10+**
- **PySide6 / PyQt6** for GUI
- **exiftool** for metadata reading/writing

---

## 📁 Project Structure
```plaintext
photo-metadata-app/
│
├── app.py                # Application entry point
├── gui/
│   ├── main_window.py    # Main UI
│   ├── image_viewer.py   # Component to display selected image
│   ├── comment_editor.py # Field to view/change metadata comment
│   └── search_panel.py   # Search input & results
│
├── core/
│   ├── metadata.py       # Functions to read/write EXIF/XMP
│   ├── file_scanner.py   # Finds images in folder
│   └── search.py         # Implements metadata search
│
├── assets/
│   └── icons/            # UI icons
│
├── requirements.txt      # Dependencies
└── README.md             # Documentation
```

---

## ⚙️ Installation
```bash
pip install -r requirements.txt
```
Dependencies:
```
PySide6
piexif
```
---

## 🛠 Packaging as a Windows .exe
You can create a Windows executable from the Python app using PyInstaller.

Basic build (single-file, no console):
```bash
pyinstaller --onefile --windowed -i"icon.ico" --name photo-metadata-search app.py
# --onefile  : produce a single .exe
# --windowed : suppress console (useful for GUI apps)
# --icon     : set the .exe icon (use .ico file)
# --name     : output executable name
```

## 🧩 How It Works
### Reading metadata:
- For JPEG/TIFF: reads EXIF `UserComment`.
- For PNG/WEBP: reads XMP `dc:description`.
- If none is present → creates it.

### Writing metadata:
- Saves comment into proper EXIF or XMP field.
- Ensures UTF-8 compatibility.

### Searching:
- Scans all files in the folder.
- Extracts comments.
- Matches by substring or keyword.

---

## 📌 Future Improvements
- Thumbnail preview grid
- SQLite index for faster search
- Drag & drop folder selection
- Tag support (multi-field metadata)
- Dark theme

---

## 📄 License
MIT License

---

## 🤝 Contributions
Pull requests welcome!
