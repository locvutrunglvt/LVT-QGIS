# -*- coding: utf-8 -*-
"""LVT4U — Thematic Map: TT 16/2023 (LDLR Style Library).

Apply categorized symbology for Vietnam's forest/land type classification
based on Circular 16/2023/TT-BNNPTNT.  Ships with 93 LDLR colour codes
and 4 pre-built QML styles.

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""

import json
import os

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QColor, QFont, QIcon, QPixmap, QPainter
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QGridLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
    QWidget, QRadioButton, QButtonGroup, QFrame,
)
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox

from ..shared.i18n import tr, current_language

# Data directory
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_QML_DIR = os.path.join(_DATA_DIR, "qml", "polygon")


def _load_master():
    """Load the LDLR master JSON."""
    path = os.path.join(_DATA_DIR, "ldlr_master.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================================
# 4 QML styles available
# =====================================================================

_STYLES = [
    {
        "id": "code_vn",
        "name_vn": "Theo mã số — Tiếng Việt",
        "name_en": "By numeric code — Vietnamese",
        "qml": "style_code_vn.qml",
        "attr_hint": "forest_typ",
        "lang": "vi",
    },
    {
        "id": "code_en",
        "name_vn": "Theo mã số — Tiếng Anh",
        "name_en": "By numeric code — English",
        "qml": "style_code_en.qml",
        "attr_hint": "Code",
        "lang": "en",
    },
    {
        "id": "ldlr_vn",
        "name_vn": "Theo mã LDLR — Tiếng Việt",
        "name_en": "By LDLR text code — Vietnamese",
        "qml": "style_ldlr_vn.qml",
        "attr_hint": "LDLR_VT",
        "lang": "vi",
    },
    {
        "id": "ldlr_en",
        "name_vn": "Theo mã LDLR — Tiếng Anh",
        "name_en": "By LDLR text code — English",
        "qml": "style_ldlr_en.qml",
        "attr_hint": "LDLR_VT",
        "lang": "en",
    },
]


def _style_name(s):
    lang = current_language()
    return s.get(f"name_{lang}", s.get("name_en", s["id"]))


# =====================================================================
# Dialog
# =====================================================================

class TT16Dialog(QDialog):
    """Compact thematic map dialog for TT 16/2023 LDLR styling."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("LVT4U — " + tr("Circular 16/2023"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(720)
        self._master = _load_master()
        self._ready = False
        self._build_ui()
        self._ready = True

    # -----------------------------------------------------------------
    # UI
    # -----------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(12, 10, 12, 10)

        # ---- Header (compact) ----
        hdr = QLabel("🎨  TT 16/2023 — LDLR Style Library")
        hdr.setFont(QFont("Arial", 12, QFont.Bold))
        hdr.setStyleSheet("color: #1565c0; padding: 2px 0;")
        root.addWidget(hdr)

        # ---- Top row: Layer + Style + Field (horizontal) ----
        top = QHBoxLayout()
        top.setSpacing(10)

        # Layer selection
        grp_layer = QGroupBox("Layer")
        gl = QVBoxLayout(grp_layer)
        gl.setContentsMargins(8, 14, 8, 6)
        gl.setSpacing(4)
        self.cmb_layer = QgsMapLayerComboBox()
        self.cmb_layer.layerChanged.connect(self._on_layer_changed)
        gl.addWidget(self.cmb_layer)
        self.lbl_geom = QLabel("")
        self.lbl_geom.setStyleSheet("color:#666; font-size:11px;")
        gl.addWidget(self.lbl_geom)
        top.addWidget(grp_layer, 2)

        # Style selection
        grp_style = QGroupBox("Style")
        gs = QVBoxLayout(grp_style)
        gs.setContentsMargins(8, 14, 8, 6)
        gs.setSpacing(4)
        self.cmb_style = QComboBox()
        for s in _STYLES:
            self.cmb_style.addItem(_style_name(s), s)
        self.cmb_style.currentIndexChanged.connect(self._on_style_changed)
        gs.addWidget(self.cmb_style)
        self.lbl_hint = QLabel("")
        self.lbl_hint.setStyleSheet("color:#888; font-size:11px;")
        gs.addWidget(self.lbl_hint)
        top.addWidget(grp_style, 3)

        # Field mapping
        grp_field = QGroupBox("Field")
        gf = QVBoxLayout(grp_field)
        gf.setContentsMargins(8, 14, 8, 6)
        gf.setSpacing(4)
        self.cmb_field = QgsFieldComboBox()
        gf.addWidget(self.cmb_field)
        self.lbl_field_type = QLabel("")
        self.lbl_field_type.setStyleSheet("color:#666; font-size:11px;")
        gf.addWidget(self.lbl_field_type)
        top.addWidget(grp_field, 2)

        root.addLayout(top)

        # ---- Buttons row ----
        btn_row = QHBoxLayout()

        self.btn_apply = QPushButton("🎨  Apply Style")
        self.btn_apply.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_apply.setMinimumHeight(34)
        self.btn_apply.setFixedWidth(160)
        self.btn_apply.setStyleSheet(
            "QPushButton{background:#1565c0;color:white;border-radius:5px;padding:6px 16px;}"
            "QPushButton:hover{background:#1976d2;}"
        )
        self.btn_apply.clicked.connect(self._apply_style)
        btn_row.addWidget(self.btn_apply)

        btn_close = QPushButton(tr("Close"))
        btn_close.setMinimumHeight(34)
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)

        btn_row.addStretch()
        root.addLayout(btn_row)

        # ---- Separator ----
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#ccc;")
        root.addWidget(line)

        # ---- Colour reference table (fills remaining space) ----
        lbl_table = QLabel("📋  LDLR — 93 codes")
        lbl_table.setFont(QFont("Arial", 10, QFont.Bold))
        lbl_table.setStyleSheet("padding: 2px 0;")
        root.addWidget(lbl_table)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(4)
        lang = current_language()
        if lang == "vi":
            self.tbl.setHorizontalHeaderLabels(["Mã", "Màu", "Tên", "HEX"])
        else:
            self.tbl.setHorizontalHeaderLabels(["Code", "Colour", "Name", "HEX"])
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setDefaultSectionSize(20)
        self.tbl.verticalHeader().setVisible(False)
        hh = self.tbl.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignLeft)
        self.tbl.setColumnWidth(0, 60)
        self.tbl.setColumnWidth(1, 30)
        self.tbl.setColumnWidth(3, 70)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        self._populate_table()
        root.addWidget(self.tbl, 1)  # stretch=1 so table fills space

        # Init state
        self._on_layer_changed(self.cmb_layer.currentLayer())
        self._on_style_changed(0)

    # -----------------------------------------------------------------
    # Colour table
    # -----------------------------------------------------------------

    def _populate_table(self, lang=None):
        """Fill colour table. *lang* follows the selected style (en/vi)."""
        if lang is None:
            lang = current_language()

        # Update header labels to match language
        if lang == "vi":
            self.tbl.setHorizontalHeaderLabels(["Mã", "Màu", "Tên", "HEX"])
        else:
            self.tbl.setHorizontalHeaderLabels(["Code", "Colour", "Name", "HEX"])

        codes = self._master["codes"]
        self.tbl.setRowCount(len(codes))

        for i, c in enumerate(codes):
            # Code
            item = QTableWidgetItem(c["code"])
            item.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(i, 0, item)

            # Colour swatch
            px = QPixmap(20, 14)
            clr = QColor(c["hex"])
            px.fill(clr)
            p = QPainter(px)
            p.setPen(QColor(120, 120, 120))
            p.drawRect(0, 0, 19, 13)
            p.end()
            ci = QTableWidgetItem()
            ci.setIcon(QIcon(px))
            ci.setBackground(clr)
            self.tbl.setItem(i, 1, ci)

            # Name — follows the selected style's language
            name = c.get(f"name_{lang}", c.get("name_en", ""))
            self.tbl.setItem(i, 2, QTableWidgetItem(name))

            # HEX
            hi = QTableWidgetItem(c["hex"])
            hi.setTextAlignment(Qt.AlignCenter)
            hi.setForeground(QColor(100, 100, 100))
            self.tbl.setItem(i, 3, hi)

    # -----------------------------------------------------------------
    # Events
    # -----------------------------------------------------------------

    def _on_layer_changed(self, layer):
        self.cmb_field.setLayer(layer)
        if layer and isinstance(layer, QgsVectorLayer):
            geom = layer.geometryType()
            names = {
                QgsWkbTypes.PointGeometry: "📍 Point",
                QgsWkbTypes.LineGeometry: "📏 Line",
                QgsWkbTypes.PolygonGeometry: "🔷 Polygon",
            }
            self.lbl_geom.setText(names.get(geom, "?"))
        else:
            self.lbl_geom.setText("—")
        self._try_auto_field()

    def _on_style_changed(self, index):
        if index < 0:
            return
        style = self.cmb_style.itemData(index)
        if not style:
            return
        hint = style.get("attr_hint", "")
        self.lbl_hint.setText(f"Trường gốc: \"{hint}\"" if hint else "")
        self._try_auto_field()

        # Switch table language to match the selected style
        style_lang = style.get("lang", current_language())
        self._populate_table(lang=style_lang)

        # Auto-apply to layer so the QGIS legend updates immediately
        if self._ready:
            self._apply_style(silent=True)

    def _try_auto_field(self):
        """Auto-select matching field based on style hint."""
        style = self.cmb_style.currentData()
        layer = self.cmb_layer.currentLayer()
        if not style or not layer:
            self.lbl_field_type.setText("")
            return

        hint = style.get("attr_hint", "")
        if not hint:
            return

        fields = [f.name() for f in layer.fields()]
        # Try exact match, then case-insensitive
        for fname in fields:
            if fname == hint:
                self.cmb_field.setField(fname)
                self.lbl_field_type.setText(f"✅ Auto: {fname}")
                return
        for fname in fields:
            if fname.lower() == hint.lower():
                self.cmb_field.setField(fname)
                self.lbl_field_type.setText(f"✅ Auto: {fname}")
                return
        self.lbl_field_type.setText(f"⚠ \"{hint}\" not found")

    # -----------------------------------------------------------------
    # Apply
    # -----------------------------------------------------------------

    def _apply_style(self, silent=False):
        layer = self.cmb_layer.currentLayer()
        if not layer:
            if not silent:
                QMessageBox.warning(self, "LVT4U", "Chọn layer trước!")
            return

        style = self.cmb_style.currentData()
        if not style:
            return

        field_name = self.cmb_field.currentField()
        qml_path = os.path.join(_QML_DIR, style["qml"])

        if not os.path.isfile(qml_path):
            if not silent:
                QMessageBox.critical(self, "LVT4U", f"QML not found:\n{qml_path}")
            return

        # Load QML style
        msg, ok = layer.loadNamedStyle(qml_path)
        if not ok:
            if not silent:
                QMessageBox.warning(self, "LVT4U", f"Load failed:\n{msg}")
            return

        # Remap attribute if different from hint
        attr_hint = style.get("attr_hint", "")
        if field_name and attr_hint and field_name != attr_hint:
            renderer = layer.renderer()
            if renderer and hasattr(renderer, 'setClassAttribute'):
                renderer.setClassAttribute(field_name)
            elif renderer and renderer.type() == 'mergedFeatureRenderer':
                emb = renderer.embeddedRenderer()
                if emb and hasattr(emb, 'setClassAttribute'):
                    emb.setClassAttribute(field_name)

        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

        if not silent:
            self.iface.messageBar().pushSuccess(
                "LVT4U",
                f"✅ Applied \"{_style_name(style)}\" → {layer.name()}"
            )

    def refresh_layers(self):
        """Called by menu launcher."""
        pass
