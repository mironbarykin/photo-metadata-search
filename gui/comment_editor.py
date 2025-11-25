from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton
from PySide6.QtCore import Signal, QTimer
from core.metadata import read_comment, write_comment

class CommentEditor(QWidget):
    comment_saved = Signal(str, str)  # image_path, comment

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Metadata Comment:")
        self.text_edit = QTextEdit()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_comment)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.text_edit)
        self.layout.addWidget(self.save_btn)
        self.current_image = None

    def load_comment(self, image_path):
        self.current_image = image_path
        comment = read_comment(image_path)
        self.text_edit.setPlainText(comment or "")

    def save_comment(self):
        if self.current_image:
            comment = self.text_edit.toPlainText()
            self.save_btn.setEnabled(False)
            self.save_btn.setText("Saving...")
            QTimer.singleShot(100, lambda: self._do_save(comment))

    def _do_save(self, comment):
        write_comment(self.current_image, comment)
        self.save_btn.setEnabled(True)
        self.save_btn.setText("Save")
        self.comment_saved.emit(self.current_image, comment)
