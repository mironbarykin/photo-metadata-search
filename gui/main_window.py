from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QPushButton, QLabel
)
from .image_viewer import ImageViewer
from .comment_editor import CommentEditor
from .search_panel import SearchPanel
from core.file_scanner import scan_images

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Metadata Viewer & Searcher")
        self.resize(900, 600)

        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.layout = QVBoxLayout(self.central)

        # Top: Folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_btn = QPushButton("Select Folder")
        self.folder_btn.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_btn)
        self.layout.addLayout(folder_layout)

        # Middle: Search panel
        self.search_panel = SearchPanel()
        self.layout.addWidget(self.search_panel)

        # Bottom: Image browser, viewer, comment editor
        content_layout = QHBoxLayout()
        self.image_viewer = ImageViewer()
        self.comment_editor = CommentEditor()
        content_layout.addWidget(self.image_viewer)
        content_layout.addWidget(self.comment_editor)
        self.layout.addLayout(content_layout)

        # Connect search panel
        self.search_panel.image_selected.connect(self.on_image_selected)
        self.image_viewer.image_selected.connect(self.on_image_selected)
        self.comment_editor.comment_saved.connect(self.on_comment_saved)

        self.images = []
        self.current_folder = None

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.current_folder = folder
            self.folder_label.setText(folder)
            self.images = scan_images(folder)
            self.search_panel.set_images(self.images)
            self.image_viewer.set_images(self.images)

    def on_image_selected(self, image_path):
        self.image_viewer.display_image(image_path)
        self.comment_editor.load_comment(image_path)

    def on_comment_saved(self, image_path, comment):
        self.search_panel.update_comment(image_path, comment)

