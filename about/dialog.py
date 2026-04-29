# -*- coding: utf-8 -*-
"""
LVT About Dialog.

Displays author information, plugin version, and language settings.

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""

import os
import configparser

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap, QFont
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
)

from ..shared.i18n import tr, current_language, set_language


class AboutDialog(QDialog):
    """About dialog showing plugin info and language settings."""

    def __init__(self, iface, plugin_dir, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.setWindowTitle(f"LVT — {tr('About')}")
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._read_metadata()
        self._build_ui()

    def _read_metadata(self):
        """Read version and description from metadata.txt."""
        meta_path = os.path.join(self.plugin_dir, "metadata.txt")
        config = configparser.ConfigParser()
        config.read(meta_path, encoding="utf-8")
        self._version = config.get("general", "version", fallback="—")
        self._description = config.get("general", "description", fallback="")
        self._author = config.get("general", "author", fallback="—")

    def _build_ui(self):
        """Construct the dialog layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)

        # --- Header ---
        header = QLabel("LVT Plugin Suite")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # --- Description ---
        desc = QLabel(self._description)
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc)

        # --- Info group ---
        info_group = QGroupBox()
        info_layout = QFormLayout(info_group)

        info_layout.addRow(
            QLabel(f"<b>{tr('Author')}:</b>"),
            QLabel(self._author),
        )
        info_layout.addRow(
            QLabel(f"<b>{tr('Version')}:</b>"),
            QLabel(self._version),
        )
        info_layout.addRow(
            QLabel(f"<b>{tr('License')}:</b>"),
            QLabel("GPL-3.0"),
        )
        main_layout.addWidget(info_group)

        # --- Language setting ---
        lang_group = QGroupBox(tr("Language"))
        lang_layout = QHBoxLayout(lang_group)

        self._lang_combo = QComboBox()
        self._lang_combo.addItem("English", "en")
        self._lang_combo.addItem("Tiếng Việt", "vi")

        # Set current selection
        current = current_language()
        idx = self._lang_combo.findData(current)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)

        lang_layout.addWidget(QLabel(f"{tr('Language')}:"))
        lang_layout.addWidget(self._lang_combo)
        main_layout.addWidget(lang_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton(tr("Apply"))
        save_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(save_btn)

        close_btn = QPushButton(tr("Close"))
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        main_layout.addLayout(btn_layout)

    def _on_apply(self):
        """Save language preference and notify user."""
        chosen = self._lang_combo.currentData()
        set_language(chosen)
        self.iface.messageBar().pushInfo(
            "LVT",
            tr("Settings saved. Restart QGIS to apply."),
        )
