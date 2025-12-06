# Photo Metadata (Editor) & Searcher

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
- **piexif** for EXIF metadata
- **Pillow** for image handling
- **exiftool** for metadata reading/writing

---

## 📁 Project Structure
```plaintext
photo-metadata-app/
│
├── app.py                # Application entry point
├── gui/
│   ├── main_window.py    # Main UI
│   └── comment_editor.py # Field to view/change metadata comment
│
├── core/
│   ├── metadata.py       # Functions to read/write EXIF/XMP
│   ├── file_scanner.py   # Finds images in folder
│   └── search.py         # Implements metadata search
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
pillow
exiftool (system dependency, install separately)
```
To install `exiftool`:
- **Windows**: Download from [exiftool.org](https://exiftool.org/)
- **macOS**: `brew install exiftool`
- **Linux**: Use your package manager, e.g. `sudo apt install libimage-exiftool-perl`

---

## 🛠 Packaging as a Windows .exe
You can create a Windows executable from the Python app using PyInstaller.

Basic build (single-file, no console):
```bash
pyinstaller --onefile --windowed -i"icon.ico" --name photo-metadata-search app.py
```

---

## 🛠 Packaging for macOS
You can create a MacOS (Unix) executable from the Python app using PyInstaller.

```bash
pyinstaller --onefile --windowed -i"icon.icns" --name photo-metadata-search app.py
```

---

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
- SQLite index for faster search
- Drag & drop folder selection
- Tag support (multi-field metadata)

---

## 📄 License
MIT License

---

## 🤝 Contributions
Pull requests welcome!

