from PySide6.QtWidgets import QListWidget, QListWidgetItem, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QPixmap

class ImageViewer(QWidget):
    image_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(96, 96))
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.layout.addWidget(self.list_widget)
        self.image_label = QLabel("Select an image")
        self.layout.addWidget(self.image_label)

    def set_images(self, image_paths):
        self.list_widget.clear()
        for path in image_paths:
            item = QListWidgetItem(path.split("/")[-1])
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                item.setIcon(pixmap.scaled(96, 96))
            item.setData(256, path)
            self.list_widget.addItem(item)

    def on_item_clicked(self, item):
        path = item.data(256)
        self.image_selected.emit(path)
        self.display_image(path)

    def display_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.image_label.setText("Cannot load image")
        else:
            self.image_label.setPixmap(pixmap.scaledToWidth(300))
