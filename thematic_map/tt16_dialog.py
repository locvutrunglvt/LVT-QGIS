# -*- coding: utf-8 -*-
"""LVT4U — Thematic Map: TT 16/2023 (LDLR Style Library).

Apply categorized symbology for Vietnam's forest/land type classification
based on Circular 16/2023/TT-BNNPTNT.

4 QML styles shipped:
  - Style LDLR_VN / EN  → classify by text code (LDLR_VT field)
  - Style code type_VN / EN → classify by numeric code (1-93)

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""

import json
import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont, QIcon, QPixmap, QPainter
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QAbstractItemView, QFrame,
)
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox

from ..shared.i18n import tr, current_language

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_QML_DIR = os.path.join(_DATA_DIR, "qml", "polygon")

# ---------------------------------------------------------------------------
# Style definitions — exactly matching the 4 QML files
# ---------------------------------------------------------------------------
_STYLES = [
    {
        "id": "ldlr_vn",
        "label_vi": "LDLR (mã chữ) — Tiếng Việt",
        "label_en": "LDLR (text code) — Vietnamese",
        "qml": "style_ldlr_vn.qml",
        "classify_attr": "LDLR_VT",      # original field in QML
        "value_type": "text",             # TXG1, TXB...
        "lang": "vi",
    },
    {
        "id": "ldlr_en",
        "label_vi": "LDLR (mã chữ) — Tiếng Anh",
        "label_en": "LDLR (text code) — English",
        "qml": "style_ldlr_en.qml",
        "classify_attr": "LDLR_VT",
        "value_type": "text",
        "lang": "en",
    },
    {
        "id": "code_vn",
        "label_vi": "Code (mã số 1–93) — Tiếng Việt",
        "label_en": "Code (numeric 1–93) — Vietnamese",
        "qml": "style_code_vn.qml",
        "classify_attr": "forest_typ",
        "value_type": "numeric",
        "lang": "vi",
    },
    {
        "id": "code_en",
        "label_vi": "Code (mã số 1–93) — Tiếng Anh",
        "label_en": "Code (numeric 1–93) — English",
        "qml": "style_code_en.qml",
        "classify_attr": "Code",
        "value_type": "numeric",
        "lang": "en",
    },
]


def _style_label(s):
    """Return display label for style based on current UI language."""
    ui = current_language()
    return s.get(f"label_{ui}", s.get("label_en", s["id"]))


def _load_master():
    """Load the LDLR master JSON (93 codes)."""
    p = os.path.join(_DATA_DIR, "ldlr_master.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================================
# Dialog
# =====================================================================

class TT16Dialog(QDialog):
    """Thematic map dialog for TT 16/2023 LDLR styling."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("LVT4U — " + tr("Circular 16/2023"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(740)
        self.setMinimumHeight(520)
        self._master = _load_master()
        self._ready = False
        self._build_ui()
        self._ready = True

    # -----------------------------------------------------------------
    # Build UI
    # -----------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(12, 10, 12, 10)

        # Header
        hdr = QLabel("🎨  TT 16/2023 — LDLR Style Library")
        hdr.setFont(QFont("Segoe UI", 12, QFont.Bold))
        hdr.setStyleSheet("color:#1565c0; padding:2px 0;")
        root.addWidget(hdr)

        # ---- Top row: Layer | Style | Field ----
        top = QHBoxLayout()
        top.setSpacing(10)

        # Layer
        grp_layer = QGroupBox("Layer")
        gl = QVBoxLayout(grp_layer)
        gl.setContentsMargins(8, 16, 8, 6)
        gl.setSpacing(4)
        self.cmb_layer = QgsMapLayerComboBox()
        self.cmb_layer.layerChanged.connect(self._on_layer_changed)
        gl.addWidget(self.cmb_layer)
        self.lbl_geom = QLabel("")
        self.lbl_geom.setStyleSheet("color:#666; font-size:11px;")
        gl.addWidget(self.lbl_geom)
        top.addWidget(grp_layer, 2)

        # Style
        grp_style = QGroupBox("Style")
        gs = QVBoxLayout(grp_style)
        gs.setContentsMargins(8, 16, 8, 6)
        gs.setSpacing(4)
        self.cmb_style = QComboBox()
        for s in _STYLES:
            self.cmb_style.addItem(_style_label(s), s)
        self.cmb_style.currentIndexChanged.connect(self._on_style_changed)
        gs.addWidget(self.cmb_style)
        self.lbl_style_info = QLabel("")
        self.lbl_style_info.setStyleSheet("color:#888; font-size:11px;")
        gs.addWidget(self.lbl_style_info)
        top.addWidget(grp_style, 3)

        # Field
        grp_field = QGroupBox("Field")
        gf = QVBoxLayout(grp_field)
        gf.setContentsMargins(8, 16, 8, 6)
        gf.setSpacing(4)
        self.cmb_field = QgsFieldComboBox()
        gf.addWidget(self.cmb_field)
        self.lbl_field_info = QLabel("")
        self.lbl_field_info.setStyleSheet("color:#666; font-size:11px;")
        gf.addWidget(self.lbl_field_info)
        top.addWidget(grp_field, 2)

        root.addLayout(top)

        # ---- Buttons ----
        btn_row = QHBoxLayout()
        self.btn_apply = QPushButton("🎨  Apply Style")
        self.btn_apply.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_apply.setMinimumHeight(36)
        self.btn_apply.setFixedWidth(160)
        self.btn_apply.setStyleSheet(
            "QPushButton{background:#1565c0;color:white;border-radius:5px;"
            "padding:6px 16px;}"
            "QPushButton:hover{background:#1976d2;}"
        )
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        btn_row.addWidget(self.btn_apply)

        btn_close = QPushButton(tr("Close"))
        btn_close.setMinimumHeight(36)
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ---- Separator ----
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#ddd;")
        root.addWidget(line)

        # ---- Reference table ----
        self.lbl_table = QLabel("📋  LDLR — 93 codes")
        self.lbl_table.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_table.setStyleSheet("padding:2px 0;")
        root.addWidget(self.lbl_table)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(4)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setDefaultSectionSize(20)
        self.tbl.verticalHeader().setVisible(False)
        hh = self.tbl.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignLeft)
        self.tbl.setColumnWidth(0, 65)
        self.tbl.setColumnWidth(1, 32)
        self.tbl.setColumnWidth(3, 72)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        root.addWidget(self.tbl, 1)

        # Init
        self._on_layer_changed(self.cmb_layer.currentLayer())
        self._on_style_changed(self.cmb_style.currentIndex())

    # -----------------------------------------------------------------
    # Populate colour table
    # -----------------------------------------------------------------
    def _populate_table(self, lang="en"):
        """Populate colour reference table with given language."""
        codes = self._master["codes"]
        self.tbl.setRowCount(len(codes))

        # Headers follow selected style language
        if lang == "vi":
            self.tbl.setHorizontalHeaderLabels(["Mã", "Màu", "Tên", "HEX"])
        else:
            self.tbl.setHorizontalHeaderLabels(["Code", "Colour", "Name", "HEX"])

        for i, c in enumerate(codes):
            # Code
            it = QTableWidgetItem(c["code"])
            it.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(i, 0, it)

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

            # Name in selected language
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
        """Layer changed → update field combo + geometry label."""
        self.cmb_field.setLayer(layer)
        if layer and isinstance(layer, QgsVectorLayer):
            geom = layer.geometryType()
            labels = {
                QgsWkbTypes.PointGeometry: "📍 Point",
                QgsWkbTypes.LineGeometry: "📏 Line",
                QgsWkbTypes.PolygonGeometry: "🔷 Polygon",
            }
            self.lbl_geom.setText(labels.get(geom, "?"))
        else:
            self.lbl_geom.setText("—")
        self._auto_detect_field()

    def _on_style_changed(self, index):
        """Style changed → update info, table language, auto-detect field."""
        if index < 0:
            return
        style = self.cmb_style.itemData(index)
        if not style:
            return

        # Show style info
        attr = style["classify_attr"]
        vtype = style["value_type"]
        self.lbl_style_info.setText(
            f"QML attr: \"{attr}\" ({vtype})"
        )

        # Update table to match style language
        self._populate_table(lang=style["lang"])

        # Auto-detect field
        self._auto_detect_field()

    def _auto_detect_field(self):
        """Try to auto-select the field matching the style's classify_attr."""
        style = self.cmb_style.currentData()
        layer = self.cmb_layer.currentLayer()
        if not style or not layer:
            self.lbl_field_info.setText("")
            return

        target = style["classify_attr"]
        fields = [f.name() for f in layer.fields()]

        # Exact match
        for f in fields:
            if f == target:
                self.cmb_field.setField(f)
                self.lbl_field_info.setText(f"✅ Match: {f}")
                return

        # Case-insensitive match
        for f in fields:
            if f.lower() == target.lower():
                self.cmb_field.setField(f)
                self.lbl_field_info.setText(f"✅ Match: {f}")
                return

        self.lbl_field_info.setText(f"⚠ \"{target}\" not found — select manually")

    # -----------------------------------------------------------------
    # Apply
    # -----------------------------------------------------------------
    def _on_apply_clicked(self):
        """User clicks Apply Style."""
        layer = self.cmb_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, "LVT4U", "Chọn layer trước / Select a layer!")
            return

        style = self.cmb_style.currentData()
        if not style:
            return

        field_name = self.cmb_field.currentField()
        if not field_name:
            QMessageBox.warning(self, "LVT4U",
                                "Chọn field trước / Select a field!")
            return

        qml_path = os.path.join(_QML_DIR, style["qml"])
        if not os.path.isfile(qml_path):
            QMessageBox.critical(self, "LVT4U", f"QML not found:\n{qml_path}")
            return

        # --- Step 1: Load QML as-is ---
        msg, ok = layer.loadNamedStyle(qml_path)
        if not ok:
            QMessageBox.warning(self, "LVT4U", f"Load style failed:\n{msg}")
            return

        # --- Step 2: Remap classify attribute if user chose different field ---
        qml_attr = style["classify_attr"]
        if field_name != qml_attr:
            renderer = layer.renderer()
            if renderer and hasattr(renderer, 'setClassAttribute'):
                renderer.setClassAttribute(field_name)

        # --- Step 3: Remove categories with no matching data ---
        self._remove_empty_categories(layer, field_name)

        # --- Step 4: Force full refresh ---
        layer.emitStyleChanged()
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())
        self.iface.mapCanvas().refresh()

        self.iface.messageBar().pushSuccess(
            "LVT4U",
            f"✅ Applied \"{_style_label(style)}\" → {layer.name()} "
            f"(field: {field_name})"
        )

    def _remove_empty_categories(self, layer, field_name):
        """Remove categories that have no matching features in the data.
        
        This ensures the legend only shows categories present in the data.
        """
        renderer = layer.renderer()
        if not renderer or not hasattr(renderer, 'categories'):
            return

        # Get unique values from the data
        idx = layer.fields().indexOf(field_name)
        if idx < 0:
            return

        unique_values = set()
        for feat in layer.getFeatures():
            val = feat[idx]
            if val is not None:
                unique_values.add(str(val))

        # Filter: keep only categories whose value exists in data
        cats = renderer.categories()
        keep_indices = []
        for i, cat in enumerate(cats):
            cat_val = str(cat.value()) if cat.value() is not None else ""
            if cat_val in unique_values:
                keep_indices.append(i)

        # Remove from end to preserve indices
        remove_indices = [i for i in range(len(cats)) if i not in keep_indices]
        for i in sorted(remove_indices, reverse=True):
            renderer.deleteCategory(i)

    # -----------------------------------------------------------------
    def refresh_layers(self):
        """Called by menu launcher."""
        pass
