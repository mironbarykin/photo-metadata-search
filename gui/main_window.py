import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QPushButton, QLabel,
    QLineEdit, QCheckBox, QScrollArea, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QPixmap
from .comment_editor import CommentEditor
from core.file_scanner import scan_images
from core.metadata import read_comment

ENABLE_UI_LOGGING = False

logger = logging.getLogger("photo_search.gui")
if ENABLE_UI_LOGGING:
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler("send_this_to_miron_ui.log", encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(fh)
else:
    logger.addHandler(logging.NullHandler())
    logger.propagate = False


MIN_COLS = 2
MAX_COLS = 6
THUMB_SIZE = 128
SPACING = 12

class ImageGridItem(QFrame):
    def __init__(self, image_path, show_note, click_callback, parent=None):
        super().__init__(parent)
        logger.debug(f"Creating ImageGridItem for {image_path}, show_note={show_note}")
        self.image_path = image_path
        self.setFrameShape(QFrame.StyledPanel)
        self.layout = QVBoxLayout(self)
        self.thumb = QLabel()
        self.name = QLabel(image_path.split("/")[-1])
        self.note = QLabel()
        self.setup_ui(show_note)
        self.mousePressEvent = lambda event: click_callback(self.image_path)

    def setup_ui(self, show_note):
        pixmap = QPixmap(self.image_path)
        self.thumb.setPixmap(pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.thumb.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.thumb)
        self.name.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.name)
        if show_note:
            comment = read_comment(self.image_path)
            self.note.setText(comment or "")
            self.note.setWordWrap(True)
            self.note.setAlignment(Qt.AlignCenter)
            self.note.setStyleSheet("font-size: 11px; color: #555;")
            self.layout.addWidget(self.note)
        else:
            self.note.hide()

    def refresh_note(self, show_note):
        if show_note:
            comment = read_comment(self.image_path)
            self.note.setText(comment or "")
            self.note.setHidden(False)
        else:
            self.note.setHidden(True)
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.debug("MainWindow initialized")
        self.setWindowTitle("Photo Metadata Viewer & Searcher")
        self.resize(1200, 700)

        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.layout = QHBoxLayout(self.central)

        # Left: Browser/search/notes
        left_panel_container = QWidget()
        left_panel = QVBoxLayout(left_panel_container)

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
        self.notes_toggle.stateChanged.connect(self.on_notes_toggle)
        search_toggle_layout.addWidget(self.search_box)
        search_toggle_layout.addWidget(self.notes_toggle)
        left_panel.addLayout(search_toggle_layout)

        # Image grid in scroll area
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(SPACING)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.grid_widget)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_panel.addWidget(self.scroll)

        self.layout.addWidget(left_panel_container, 2)

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
        self.grid_items = {}
        self.loaded_count = 0
        self.preloaded_count = 0
        self.cols = 4
        self.batch_size = 20 

        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.scroll.viewport().installEventFilter(self)
        self.resizeEvent = self.on_resize

    def eventFilter(self, obj, event):
        logger.debug(f"eventFilter: obj={obj}, event={event.type()}")

        if obj is self.scroll.viewport() and event.type() == QEvent.Resize:
            self.update_columns()
        return super().eventFilter(obj, event)

    def on_resize(self, event):
        self.update_columns()
        event.accept()

    def update_columns(self):
        logger.debug("Updating columns")

        width = self.scroll.viewport().width()
        height = self.scroll.viewport().height()
        col = max(MIN_COLS, min(MAX_COLS, width // (THUMB_SIZE + SPACING)))
        if col != self.cols:
            self.cols = col
            self.relayout_grid()
        self.grid_widget.setMinimumWidth(width)
        self.grid_widget.setMaximumWidth(width)
        row_height = THUMB_SIZE + SPACING
        visible_rows = max(1, (height // row_height) + 2)
        self.batch_size = self.cols * visible_rows


    def relayout_grid(self):
        for idx, path in enumerate(self.filtered_images[:self.loaded_count]):
            row, col = divmod(idx, self.cols)
            item = self.grid_items.get(path)
            if item:
                self.grid_layout.addWidget(item, row, col)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.current_folder = folder
            self.folder_label.setText(folder)
            self.images = scan_images(folder)
            self.loaded_count = 0
            self.preloaded_count = 0
            self.refresh_grid()

    def on_notes_toggle(self, state):
        logger.debug(f"Notes toggle: {state}. Refreshing grid.")
        self.refresh_grid()

    def refresh_grid(self):
        text = self.search_box.text().strip().lower()
        show_note = self.notes_toggle.isChecked()
        logger.debug(f"Refreshing grid. Search text: '{text}' show_note state: {show_note}")
        self.filtered_images = []
        for path in self.images:
            comment = read_comment(path)
            if not text or (comment and text in comment.lower()):
                self.filtered_images.append(path)
        # Properly delete widgets to prevent them from becoming windows
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                self.grid_layout.removeWidget(widget)
                widget.deleteLater()  # <-- Only this, do NOT call setParent(None)
        self.grid_items.clear()
        self.loaded_count = 0
        self.preloaded_count = 0
        self.update_columns()
        self.load_more_images()

    def load_more_images(self, preload=False):
        logger.debug(f"Loading more images, preload={preload}")
        show_note = self.notes_toggle.isChecked()
        cols = self.cols
        total = len(self.filtered_images)
        batch_size = self.batch_size
        if preload:
            start = self.preloaded_count
            end = min(start + batch_size, total)
            for idx, path in enumerate(self.filtered_images[start:end], start=start):
                if path not in self.grid_items:
                    QPixmap(path).scaled(THUMB_SIZE, THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preloaded_count = end
            return

        start = self.loaded_count
        end = min(start + batch_size, total)
        for idx, path in enumerate(self.filtered_images[start:end], start=start):
            row, col = divmod(idx, cols)
            item = ImageGridItem(path, show_note, self.on_image_selected, parent=self.grid_widget)
            self.grid_layout.addWidget(item, row, col)
            self.grid_items[path] = item
        self.loaded_count = end
        if self.loaded_count < total:
            QTimer.singleShot(0, lambda: self.load_more_images(preload=True))

    def on_scroll(self, value):
        logger.debug(f"Scroll value changed: {value}")
        scroll_bar = self.scroll.verticalScrollBar()
        if scroll_bar.maximum() - value < 200:
            if self.loaded_count < len(self.filtered_images):
                self.load_more_images()

    def on_image_selected(self, image_path):
        logger.debug(f"Image selected: {image_path}")
        self.selected_image = image_path
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.preview_label.setText("Cannot load image")
            self.preview_label.setPixmap(QPixmap())
        else:
            self.preview_label.setPixmap(pixmap.scaledToWidth(400, Qt.SmoothTransformation))
        self.comment_editor.load_comment(image_path)

    def on_comment_saved(self, image_path, comment):
        logger.debug(f"Comment saved for {image_path}: {comment}")
        show_note = self.notes_toggle.isChecked()
        item = self.grid_items.get(image_path)
        if item:
            item.refresh_note(show_note)

