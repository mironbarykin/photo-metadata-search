from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem
from PySide6.QtCore import Signal
from core.metadata import read_comment

class SearchPanel(QWidget):
    image_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by comment...")
        self.search_box.textChanged.connect(self.on_search)
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.layout.addWidget(self.search_box)
        self.layout.addWidget(self.list_widget)
        self.images = []

    def set_images(self, image_paths):
        self.images = image_paths
        self.refresh_list(self.images)

    def refresh_list(self, images):
        self.list_widget.clear()
        for path in images:
            comment = read_comment(path)
            text = f"{path.split('/')[-1]}: {comment or ''}"
            item = QListWidgetItem(text)
            item.setData(256, path)
            self.list_widget.addItem(item)

    def on_search(self, text):
        filtered = []
        for path in self.images:
            comment = read_comment(path)
            if text.strip() == "" or (comment and text.lower() in comment.lower()):
                filtered.append(path)
        self.refresh_list(filtered)

    def on_item_clicked(self, item):
        path = item.data(256)
        self.image_selected.emit(path)

    def update_comment(self, image_path, comment):
        # Refresh the list if a comment was updated
        self.on_search(self.search_box.text())
