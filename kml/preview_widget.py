"""Preview widget for HTML popup descriptions.

Shows rendered HTML using QTextBrowser with record navigation.
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QPushButton, QLabel
)
from qgis.PyQt.QtCore import Qt
from .html_template import HtmlTemplateBuilder


class PreviewDialog(QDialog):
    """Preview dialog showing rendered HTML popup."""

    def __init__(self, config, features_data, parent=None):
        """
        Args:
            config: Plugin configuration dict
            features_data: List of dicts [{field: value, ...}, ...]
        """
        super().__init__(parent)
        self.config = config
        self.features_data = features_data
        self.current_index = 0
        self.html_builder = HtmlTemplateBuilder(config)

        self.setWindowTitle('Preview Popup - LVT4U KML view')
        self.setMinimumSize(480, 420)
        self._setup_ui()
        self._update_preview()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel('<b>Xem trước Popup HTML</b>')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size:14px;padding:5px')
        layout.addWidget(title)

        # Navigation bar
        nav = QHBoxLayout()
        self.btn_prev = QPushButton('◀ Trước')
        self.btn_prev.clicked.connect(self._go_prev)
        self.lbl_index = QLabel('1 / 1')
        self.lbl_index.setAlignment(Qt.AlignCenter)
        self.lbl_index.setStyleSheet('font-weight:bold')
        self.btn_next = QPushButton('Tiếp ▶')
        self.btn_next.clicked.connect(self._go_next)

        nav.addWidget(self.btn_prev)
        nav.addStretch()
        nav.addWidget(self.lbl_index)
        nav.addStretch()
        nav.addWidget(self.btn_next)
        layout.addLayout(nav)

        # HTML browser
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setStyleSheet('background:#f0f0f0;border:1px solid #ccc;border-radius:4px')
        layout.addWidget(self.browser)

        # Close button
        btn_close = QPushButton('Đóng')
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet('padding:6px 20px')
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)

    def _update_preview(self):
        """Render current feature's HTML popup."""
        total = len(self.features_data)
        if total == 0:
            self.browser.setHtml('<p style="color:#999;text-align:center">Không có dữ liệu</p>')
            self.lbl_index.setText('0 / 0')
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            return

        self.current_index = max(0, min(self.current_index, total - 1))
        self.lbl_index.setText(f'{self.current_index + 1} / {total}')
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < total - 1)

        feature_data = self.features_data[self.current_index]
        html = self.html_builder.build(feature_data)

        # Wrap in a styled container simulating Google Earth popup
        wrapped = (
            '<div style="background:#e8e8e8;padding:15px;font-family:sans-serif">'
            '<div style="background:white;border-radius:6px;padding:8px;'
            'box-shadow:0 2px 6px rgba(0,0,0,0.2)">'
            f'{html}</div></div>'
        )
        self.browser.setHtml(wrapped)

    def _go_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._update_preview()

    def _go_next(self):
        if self.current_index < len(self.features_data) - 1:
            self.current_index += 1
            self._update_preview()
