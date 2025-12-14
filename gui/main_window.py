import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QPushButton, QLabel,
    QLineEdit, QCheckBox, QScrollArea, QGridLayout, QFrame
)
from PySide6.QtCore import (
    Qt, QEvent, QTimer, QObject, Signal, QRunnable, Slot, QSize, QThreadPool
)
from PySide6.QtGui import QPixmap, QGuiApplication, QImageReader, QImage
from .comment_editor import CommentEditor
from core.file_scanner import scan_images
from core.metadata import read_comment
import os
import platform
import subprocess
import hashlib
import pathlib
import html
import re

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

def highlight_text(text: str, query: str) -> str:
    if not text or not query:
        return html.escape(text or "")

    escaped = html.escape(text)
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    return pattern.sub(
        lambda m: f"<span style='background-color: #ffe066;'>{m.group(0)}</span>",
        escaped
    )

def open_in_explorer(path):
    """Open a file in Finder/Explorer/your file manager."""
    system = platform.system()

    if system == "Windows":
        # Select the file in Explorer
        subprocess.run(["explorer", "/select,", os.path.normpath(path)])
    elif system == "Darwin":
        # Reveal in Finder
        subprocess.run(["open", "-R", path])
    else:
        # Linux (xdg-open just opens the file or folder)
        folder = os.path.dirname(path)
        subprocess.run(["xdg-open", folder])


class ThumbnailSignals(QObject):
    finished = Signal(str, QPixmap)  # path, pixmap


class ThumbnailWorker(QRunnable):
    """
    QRunnable that reads and scales an image using QImageReader (decode at scaled size).
    Emits finished(path, pixmap) on completion.
    """

    def __init__(self, path: str, size: int, disk_cache_path: str = None):
        super().__init__()
        self.path = path
        self.size = size
        self.signals = ThumbnailSignals()
        self.disk_cache_path = disk_cache_path

    @Slot()
    def run(self):
        try:
            # Attempt to use QImageReader scaled decode
            reader = QImageReader(self.path)
            # request integer scaled size preserving aspect ratio by setting max dimension
            # We set scaled size with equal width/height - QImageReader will preserve aspect ratio
            reader.setAutoTransform(True)
            reader.setScaledSize(QSize(self.size, self.size))
            image = reader.read()
            if image and not image.isNull():
                pix = QPixmap.fromImage(image)
            else:
                # Fallback: QPixmap direct load (rare)
                pix = QPixmap(self.path)
                if not pix.isNull():
                    pix = pix.scaled(self.size, self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # Emit result (main thread will store in cache)
            if pix and not pix.isNull():
                self.signals.finished.emit(self.path, pix)
        except Exception as e:
            logger.exception(f"ThumbnailWorker failed for {self.path}: {e}")

class ImageGridItem(QFrame):
    def __init__(self, image_path, show_note, click_callback, search_text="", parent=None):
        super().__init__(parent)
        logger.debug(f"Creating ImageGridItem for {image_path}, show_note={show_note}")
        self.image_path = image_path
        self.setFrameShape(QFrame.StyledPanel)
        self.layout = QVBoxLayout(self)
        self.thumb = QLabel()
        self.name = QLabel(os.path.basename(image_path))
        self.note = QLabel()
        self.note.setTextFormat(Qt.RichText)
        # placeholder pixmap to show immediately
        placeholder = QPixmap(THUMB_SIZE, THUMB_SIZE)
        placeholder.fill(Qt.lightGray)
        self.thumb.setPixmap(placeholder)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.thumb)
        self.name.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.name)

        if show_note:
            # read_comment can be expensive; but leaving for now
            try:
                comment = read_comment(self.image_path)
            except Exception:
                comment = None
            self.note.setText(highlight_text(comment or "", search_text))
            self.note.setWordWrap(True)
            self.note.setAlignment(Qt.AlignCenter)
            self.note.setStyleSheet("font-size: 11px; color: #555;")
            self.layout.addWidget(self.note)
        else:
            self.note.hide()

        self.mousePressEvent = lambda event: click_callback(self.image_path)

    def set_thumbnail(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            # scale once more to ensure exact fit while keeping aspect
            scaled = pixmap.scaled(THUMB_SIZE, THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumb.setPixmap(scaled)

    def refresh_note(self, show_note, search_text=""):
        if show_note:
            comment = read_comment(self.image_path)
            self.note.setText(highlight_text(comment or "", search_text))
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
        self.filename_label = QLabel("")
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.filename_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.filename_label.mousePressEvent = self.copy_filename_to_clipboard

        right_panel.addWidget(self.filename_label)

        self.preview_label = QLabel("Select an image")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        right_panel.addWidget(self.preview_label)
        self.open_btn = QPushButton("Open in File Explorer")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.on_open_clicked)
        right_panel.addWidget(self.open_btn)
        self.comment_editor = CommentEditor()
        right_panel.addWidget(self.comment_editor)
        self.layout.addLayout(right_panel, 1)

        # Signals
        self.comment_editor.comment_saved.connect(self.on_comment_saved)

        # image state
        self.images = []
        self.filtered_images = []
        self.current_folder = None
        self.selected_image = None
        self.grid_items = {}
        self.loaded_count = 0
        self.preloaded_count = 0
        self.cols = 4
        self.batch_size = 20

        # thumbnail cache + threadpool
        self.thumb_cache = {}  # path -> QPixmap
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max(2, os.cpu_count() or 2))
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "photo_meta_thumbs")
        pathlib.Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.scroll.viewport().installEventFilter(self)
        self.resizeEvent = self.on_resize

    def on_open_clicked(self):
        if self.selected_image:
            open_in_explorer(self.selected_image)

    def copy_filename_to_clipboard(self, event):
        if self.selected_image:
            QGuiApplication.clipboard().setText(self.selected_image)
            # Optional: brief user feedback
            self.filename_label.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: green;"
            )
            QTimer.singleShot(400, lambda:
                self.filename_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            )

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
            # clear thumbnail cache for changed folder? We'll keep cache but it's keyed by full path.
            self.refresh_grid()

    def on_notes_toggle(self, state):
        logger.debug(f"Notes toggle: {state}. Refreshing grid.")
        self.refresh_grid()

    def refresh_grid(self):
        text = self.search_box.text().strip().lower()
        show_note = self.notes_toggle.isChecked()
        logger.debug(f"Refreshing grid. Search text: '{text}' show_note state: {show_note}")
        # Filter images (note: read_comment may be slow for many images; consider moving filtering to a background thread if that's an issue)
        self.filtered_images = []
        for path in self.images:
            try:
                comment = read_comment(path)
            except Exception:
                comment = None
            if not text or (comment and text in comment.lower()):
                self.filtered_images.append(path)
        # Properly delete widgets to prevent them from becoming windows
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                self.grid_layout.removeWidget(widget)
                widget.deleteLater()
        self.grid_items.clear()
        self.loaded_count = 0
        self.preloaded_count = 0
        self.update_columns()
        self.load_more_images()

    # helpers for disk cache naming & validation
    def _cache_filename_for(self, path: str) -> str:
        # Use a hash so long paths don't break filenames
        key = hashlib.sha1(path.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{key}.png")

    def _is_disk_cache_valid(self, path: str, cache_file: str) -> bool:
        if not os.path.exists(cache_file):
            return False
        try:
            src_mtime = int(os.path.getmtime(path))
            cache_mtime = int(os.path.getmtime(cache_file))
            # If cache older than source, invalid
            return cache_mtime >= src_mtime
        except Exception:
            return False

    def _load_from_disk_cache(self, path: str):
        cache_file = self._cache_filename_for(path)
        if self._is_disk_cache_valid(path, cache_file):
            pix = QPixmap(cache_file)
            if not pix.isNull():
                return pix
        return None

    def _save_to_disk_cache(self, path: str, pixmap: QPixmap):
        try:
            cache_file = self._cache_filename_for(path)
            # Save QPixmap -> QImage -> file
            image = pixmap.toImage()
            image.save(cache_file, "PNG")
            # Update mtime to match source mtime for validation
            try:
                src_mtime = os.path.getmtime(path)
                os.utime(cache_file, (src_mtime, src_mtime))
            except Exception:
                pass
        except Exception:
            logger.exception(f"Failed to save thumbnail cache for {path}")

    def _on_thumbnail_ready(self, path: str, pixmap: QPixmap):
        # Called in main thread via signal
        if pixmap is None or pixmap.isNull():
            return
        # store in memory cache
        self.thumb_cache[path] = pixmap
        # save to disk cache (async worker created pixmap; saving maybe expensive but small PNGs)
        try:
            self._save_to_disk_cache(path, pixmap)
        except Exception:
            logger.exception("Disk cache save error")
        # update widget if present
        item = self.grid_items.get(path)
        if item:
            item.set_thumbnail(pixmap)

    def load_more_images(self, preload=False):
        logger.debug(f"Loading more images, preload={preload}")
        show_note = self.notes_toggle.isChecked()
        search_text = self.search_box.text().strip()
        cols = self.cols
        total = len(self.filtered_images)
        batch_size = self.batch_size
        if preload:
            start = self.preloaded_count
            end = min(start + batch_size, total)
            # Preload thumbnails into cache without creating widgets
            for idx, path in enumerate(self.filtered_images[start:end], start=start):
                if path in self.thumb_cache:
                    continue
                # try disk cache first
                pix = self._load_from_disk_cache(path)
                if pix:
                    self.thumb_cache[path] = pix
                    continue
                # schedule worker to create thumbnail
                worker = ThumbnailWorker(path, THUMB_SIZE, disk_cache_path=self.cache_dir)
                worker.signals.finished.connect(self._on_thumbnail_ready)
                self.pool.start(worker)
            self.preloaded_count = end
            return

        start = self.loaded_count
        end = min(start + batch_size, total)
        for idx, path in enumerate(self.filtered_images[start:end], start=start):
            row, col = divmod(idx, cols)
            item = ImageGridItem(path, show_note, self.on_image_selected, search_text=search_text, parent=self.grid_widget)
            self.grid_layout.addWidget(item, row, col)
            self.grid_items[path] = item
            # if in-memory cache, set immediately
            pix = self.thumb_cache.get(path)
            if pix:
                item.set_thumbnail(pix)
                continue
            # try disk cache
            pix = self._load_from_disk_cache(path)
            if pix:
                # store and apply
                self.thumb_cache[path] = pix
                item.set_thumbnail(pix)
                continue
            # schedule worker to create thumbnail
            worker = ThumbnailWorker(path, THUMB_SIZE, disk_cache_path=self.cache_dir)
            worker.signals.finished.connect(self._on_thumbnail_ready)
            self.pool.start(worker)

        self.loaded_count = end
        if self.loaded_count < total:
            # schedule background preload of next batch (non-blocking)
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
        self.filename_label.setText(os.path.basename(image_path))
        # For preview (bigger), we will load synchronously but scaled to width to keep it snappy.
        # If you find preview blocks, we can make this async too.
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.preview_label.setText("Cannot load image")
            self.preview_label.setPixmap(QPixmap())
        else:
            self.preview_label.setPixmap(pixmap.scaledToWidth(400, Qt.SmoothTransformation))
        self.open_btn.setEnabled(True)
        self.comment_editor.load_comment(image_path)

    def on_comment_saved(self, image_path, comment):
        logger.debug(f"Comment saved for {image_path}: {comment}")
        show_note = self.notes_toggle.isChecked()
        search_text = self.search_box.text().strip()
        item = self.grid_items.get(image_path)
        if item:
                item.refresh_note(show_note, search_text)
