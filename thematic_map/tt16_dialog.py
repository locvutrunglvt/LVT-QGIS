# -*- coding: utf-8 -*-
"""LVT4U — Thematic Map: TT 16/2023 (LDLR Style Library).

Apply categorized symbology for Vietnam's forest/land type classification
based on Circular 16/2023/TT-BNNPTNT.

4 QML styles:
  - LDLR VN/EN → classify by text code (LDLR_VT)
  - Code VN/EN → classify by numeric code (1–93)

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
from qgis.core import QgsVectorLayer, QgsWkbTypes
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox

from ..shared.i18n import tr, current_language

# ---------------------------------------------------------------------------
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_QML_DIR = os.path.join(_DATA_DIR, "qml", "polygon")

# ---------------------------------------------------------------------------
# Style definitions
# ---------------------------------------------------------------------------
_STYLES = [
    {
        "id": "ldlr_vn",
        "label_vi": "LDLR (mã chữ) — Tiếng Việt",
        "label_en": "LDLR (text code) — Vietnamese",
        "qml": "style_ldlr_vn.qml",
        "classify_attr": "LDLR_VT",
        "value_type": "text",       # text_code column in master
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
        "value_type": "numeric",    # num_code column in master
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
    ui = current_language()
    return s.get(f"label_{ui}", s.get("label_en", s["id"]))


def _load_master():
    p = os.path.join(_DATA_DIR, "ldlr_master.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


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
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(12, 10, 12, 10)

        # Header
        hdr = QLabel("🎨  TT 16/2023 — LDLR Style Library")
        hdr.setFont(QFont("Segoe UI", 12, QFont.Bold))
        hdr.setStyleSheet("color:#1565c0; padding:2px 0;")
        root.addWidget(hdr)

        # Top row: Layer | Style | Field
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

        # Buttons
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

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#ddd;")
        root.addWidget(line)

        # Reference table
        self.lbl_table = QLabel("")
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
    # Colour table — adapts to style type AND language
    # -----------------------------------------------------------------
    def _populate_table(self, style):
        """Populate table based on style: show text_code or num_code,
        and names in the style's language."""
        codes = self._master["codes"]
        lang = style["lang"]
        vtype = style["value_type"]

        self.tbl.setRowCount(len(codes))

        # Headers
        if lang == "vi":
            code_hdr = "Mã số" if vtype == "numeric" else "Mã"
            self.tbl.setHorizontalHeaderLabels([code_hdr, "Màu", "Tên", "HEX"])
            self.lbl_table.setText(
                f"📋  LDLR — 93 mã ({'số 1–93' if vtype == 'numeric' else 'chữ'})"
            )
        else:
            code_hdr = "Code" if vtype == "numeric" else "LDLR"
            self.tbl.setHorizontalHeaderLabels([code_hdr, "Colour", "Name", "HEX"])
            self.lbl_table.setText(
                f"📋  LDLR — 93 codes ({'numeric 1–93' if vtype == 'numeric' else 'text'})"
            )

        for i, c in enumerate(codes):
            # Code column: show num_code or text_code based on style
            if vtype == "numeric":
                code_val = c.get("num_code", "")
            else:
                code_val = c.get("text_code", c.get("code", ""))

            it = QTableWidgetItem(str(code_val))
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

            # Name in style's language
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
        if index < 0:
            return
        style = self.cmb_style.itemData(index)
        if not style:
            return

        attr = style["classify_attr"]
        vtype = "mã số" if style["value_type"] == "numeric" else "mã chữ"
        self.lbl_style_info.setText(f"QML field: \"{attr}\" ({vtype})")

        # Update table to match style
        self._populate_table(style)

        # Auto-detect field
        self._auto_detect_field()

    def _auto_detect_field(self):
        style = self.cmb_style.currentData()
        layer = self.cmb_layer.currentLayer()
        if not style or not layer:
            self.lbl_field_info.setText("")
            return

        target = style["classify_attr"]
        fields = [f.name() for f in layer.fields()]

        for f in fields:
            if f == target:
                self.cmb_field.setField(f)
                self.lbl_field_info.setText(f"✅ Match: {f}")
                return
        for f in fields:
            if f.lower() == target.lower():
                self.cmb_field.setField(f)
                self.lbl_field_info.setText(f"✅ Match: {f}")
                return

        self.lbl_field_info.setText(f"⚠ \"{target}\" — chọn field tương ứng")

    # -----------------------------------------------------------------
    # Apply
    # -----------------------------------------------------------------
    def _on_apply_clicked(self):
        layer = self.cmb_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, "LVT4U", "Chọn layer / Select a layer!")
            return

        style = self.cmb_style.currentData()
        if not style:
            return

        field_name = self.cmb_field.currentField()
        if not field_name:
            QMessageBox.warning(self, "LVT4U",
                                "Chọn field / Select a field!")
            return

        qml_path = os.path.join(_QML_DIR, style["qml"])
        if not os.path.isfile(qml_path):
            QMessageBox.critical(self, "LVT4U", f"QML not found:\n{qml_path}")
            return

        # ----------------------------------------------------------
        # Step 1: Load QML via QDomDocument (most reliable method)
        # ----------------------------------------------------------
        from qgis.PyQt.QtXml import QDomDocument
        from qgis.core import QgsReadWriteContext

        doc = QDomDocument()
        with open(qml_path, "r", encoding="utf-8") as f:
            content = f.read()
        success, err_msg, err_line, err_col = doc.setContent(content)
        if not success:
            QMessageBox.critical(
                self, "LVT4U",
                f"QML parse error at line {err_line}:\n{err_msg}"
            )
            return

        # Import style from parsed document
        msg, ok = layer.importNamedStyle(doc)
        if not ok:
            QMessageBox.warning(self, "LVT4U", f"Import failed:\n{msg}")
            return

        # ----------------------------------------------------------
        # Step 2: Remap classify attribute if user chose different field
        # ----------------------------------------------------------
        qml_attr = style["classify_attr"]
        if field_name != qml_attr:
            renderer = layer.renderer()
            if renderer and hasattr(renderer, 'setClassAttribute'):
                renderer.setClassAttribute(field_name)

        # ----------------------------------------------------------
        # Step 3: Remove categories with no matching features
        # ----------------------------------------------------------
        self._remove_empty_categories(layer, field_name)

        # ----------------------------------------------------------
        # Step 4: Force complete refresh
        # ----------------------------------------------------------
        layer.emitStyleChanged()
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())
        self.iface.mapCanvas().refresh()

        # Diagnostic: verify first category label
        renderer = layer.renderer()
        diag = ""
        if renderer and hasattr(renderer, 'categories'):
            cats = renderer.categories()
            if cats:
                diag = f" | Legend[0]: \"{cats[0].label()[:40]}\""

        self.iface.messageBar().pushSuccess(
            "LVT4U",
            f"✅ {_style_label(style)} → {layer.name()} [{field_name}]{diag}"
        )

    @staticmethod
    def _normalize(val):
        """Normalize a value to a comparable string.

        Handles type mismatch:
          int/float 14 or 14.0 → "14"
          str "14"             → "14"
          str "TXG1"           → "TXG1"
          NULL / None          → ""
        """
        if val is None:
            return ""
        # Try numeric normalization (14.0 → "14", 3.0 → "3")
        try:
            f = float(val)
            if f == int(f):
                return str(int(f))
            return str(f)
        except (ValueError, TypeError):
            return str(val).strip()

    def _remove_empty_categories(self, layer, field_name):
        """Keep only categories whose value exists in the data."""
        renderer = layer.renderer()
        if not renderer or not hasattr(renderer, 'categories'):
            return

        idx = layer.fields().indexOf(field_name)
        if idx < 0:
            return

        # Collect unique normalized values from data
        unique_vals = set()
        for feat in layer.getFeatures():
            unique_vals.add(self._normalize(feat[idx]))

        # Remove unmatched categories (from end to keep indices valid)
        cats = renderer.categories()
        to_remove = []
        for i, cat in enumerate(cats):
            cat_val = self._normalize(cat.value())
            if cat_val not in unique_vals:
                to_remove.append(i)

        for i in sorted(to_remove, reverse=True):
            renderer.deleteCategory(i)

    # -----------------------------------------------------------------
    def refresh_layers(self):
        pass


