from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QPushButton, QLabel,
    QLineEdit, QCheckBox, QScrollArea, QGridLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from .comment_editor import CommentEditor
from core.file_scanner import scan_images
from core.metadata import read_comment

class ImageGridItem(QFrame):
    def __init__(self, image_path, show_note, click_callback):
        super().__init__()
        self.image_path = image_path
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        pixmap = QPixmap(image_path)
        thumb = QLabel()
        thumb.setPixmap(pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        thumb.setAlignment(Qt.AlignCenter)
        layout.addWidget(thumb)
        name = QLabel(image_path.split("/")[-1])
        name.setAlignment(Qt.AlignCenter)
        layout.addWidget(name)
        if show_note:
            comment = read_comment(image_path)
            note = QLabel(comment or "")
            note.setWordWrap(True)
            note.setAlignment(Qt.AlignCenter)
            note.setStyleSheet("font-size: 11px; color: #555;")
            layout.addWidget(note)
        self.mousePressEvent = lambda event: click_callback(self.image_path)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Metadata Viewer & Searcher")
        self.resize(1200, 700)

        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.layout = QHBoxLayout(self.central)

        # Left: Browser/search/notes
        left_panel = QVBoxLayout()
        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_btn = QPushButton("Select Folder")
        self.folder_btn.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_btn)
        left_panel.addLayout(folder_layout)

        # Search and notes toggle
        search_toggle_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by comment...")
        self.search_box.textChanged.connect(self.refresh_grid)
        self.notes_toggle = QCheckBox("Show notes")
        self.notes_toggle.setChecked(True)
        self.notes_toggle.stateChanged.connect(self.refresh_grid)
        search_toggle_layout.addWidget(self.search_box)
        search_toggle_layout.addWidget(self.notes_toggle)
        left_panel.addLayout(search_toggle_layout)

        # Image grid in scroll area
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.grid_widget)
        left_panel.addWidget(self.scroll)

        # Add left panel to main layout
        self.layout.addLayout(left_panel, 2)

        # Right: Preview and comment editor
        right_panel = QVBoxLayout()
        self.preview_label = QLabel("Select an image")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        right_panel.addWidget(self.preview_label)
        self.comment_editor = CommentEditor()
        right_panel.addWidget(self.comment_editor)
        self.layout.addLayout(right_panel, 1)

        # Signals
        self.comment_editor.comment_saved.connect(self.on_comment_saved)

        self.images = []
        self.filtered_images = []
        self.current_folder = None
        self.selected_image = None

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.current_folder = folder
            self.folder_label.setText(folder)
            self.images = scan_images(folder)
            self.refresh_grid()

    def refresh_grid(self):
        # Filter images by search
        text = self.search_box.text().strip().lower()
        show_note = self.notes_toggle.isChecked()
        self.filtered_images = []
        for path in self.images:
            comment = read_comment(path)
            if not text or (comment and text in comment.lower()):
                self.filtered_images.append(path)
        # Clear grid
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        # Add filtered images to grid
        cols = 4
        for idx, path in enumerate(self.filtered_images):
            row, col = divmod(idx, cols)
            item = ImageGridItem(path, show_note, self.on_image_selected)
            self.grid_layout.addWidget(item, row, col)

    def on_image_selected(self, image_path):
        self.selected_image = image_path
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.preview_label.setText("Cannot load image")
            self.preview_label.setPixmap(QPixmap())
        else:
            self.preview_label.setPixmap(pixmap.scaledToWidth(400, Qt.SmoothTransformation))
        self.comment_editor.load_comment(image_path)

    def on_comment_saved(self, image_path, comment):
        # Refresh grid to update notes if visible
        self.refresh_grid()

