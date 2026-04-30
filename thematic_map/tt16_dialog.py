# -*- coding: utf-8 -*-
"""LVT4U — Thematic Map: TT 16/2023 (LDLR Style Library).

Apply categorized symbology for Vietnam's forest/land type classification
based on Circular 16/2023/TT-BNNPTNT.  Ships with 93 LDLR colour codes
and pre-built QML styles for polygon, line, and point layers.

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
    QSplitter, QWidget, QFormLayout, QRadioButton, QButtonGroup,
    QApplication,
)
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsWkbTypes, QgsMapLayerProxyModel,
)
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox

from ..shared.i18n import tr, current_language

# Data directory
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_QML_DIR = os.path.join(_DATA_DIR, "qml")


def _load_master():
    """Load the LDLR master JSON."""
    path = os.path.join(_DATA_DIR, "ldlr_master.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================================
# Style Catalog — maps user-friendly names to QML files
# =====================================================================

_POLYGON_STYLES = [
    {
        "id": "ldlr_fill_code",
        "name_vn": "LDLR — Tô vùng theo mã số (forest_typ)",
        "name_en": "LDLR — Fill by numeric code (forest_typ)",
        "qml": "polygon/ldlr_by_code_vn.qml",
        "attr_hint": "forest_typ",
        "description_vn": "93 loại đất rừng — phân loại theo mã số (1-93)",
        "description_en": "93 forest/land types — classified by numeric code (1-93)",
    },
    {
        "id": "ldlr_fill_text",
        "name_vn": "LDLR — Tô vùng theo mã viết tắt (LDLR_VT)",
        "name_en": "LDLR — Fill by text code (LDLR_VT)",
        "qml": "polygon/ldlr_by_text_vn.qml",
        "attr_hint": "forest_typ",
        "description_vn": "93 loại đất rừng — phân loại theo mã chữ (TXG1, RTG...)",
        "description_en": "93 forest/land types — classified by text code (TXG1, RTG...)",
    },
]

_LINE_STYLES = [
    {
        "id": "ldlr_line_vn",
        "name_vn": "LDLR — Đường viền (tiếng Việt)",
        "name_en": "LDLR — Line border (Vietnamese)",
        "qml": "line/ldlr_line_vn.qml",
        "attr_hint": "LDLR_VT",
    },
    {
        "id": "ldlr_line_en",
        "name_vn": "LDLR — Đường viền (tiếng Anh)",
        "name_en": "LDLR — Line border (English)",
        "qml": "line/ldlr_line_en.qml",
        "attr_hint": "LDLR_VT",
    },
    {
        "id": "ldlr_code_line_vn",
        "name_vn": "LDLR — Đường viền theo mã số (tiếng Việt)",
        "name_en": "LDLR — Line by code (Vietnamese)",
        "qml": "line/ldlr_code_line_vn.qml",
        "attr_hint": "forest_typ",
    },
    {
        "id": "ldlr_code_line_en",
        "name_vn": "LDLR — Đường viền theo mã số (tiếng Anh)",
        "name_en": "LDLR — Line by code (English)",
        "qml": "line/ldlr_code_line_en.qml",
        "attr_hint": "Code",
    },
    {
        "id": "ranh_tinh_huyen_xa",
        "name_vn": "Ranh giới tỉnh / huyện / xã",
        "name_en": "Province / District / Commune boundary",
        "qml": "line/ranh_tinh_huyen_xa.qml",
        "attr_hint": "ten",
    },
    {
        "id": "ranh_huyen_xa",
        "name_vn": "Ranh giới huyện / xã",
        "name_en": "District / Commune boundary",
        "qml": "line/ranh_huyen_xa.qml",
        "attr_hint": "ten",
    },
    {
        "id": "ranh_cnl",
        "name_vn": "Ranh giới 3 loại rừng (CNL)",
        "name_en": "Forest function boundary (CNL)",
        "qml": "line/ranh_cnl.qml",
        "attr_hint": "TEN",
    },
    {
        "id": "ranh_tkkl",
        "name_vn": "Ranh giới tiểu khu / khoảnh",
        "name_en": "Sub-compartment / Compartment boundary",
        "qml": "line/ranh_tkkl.qml",
        "attr_hint": "ten",
    },
    {
        "id": "giao_thong",
        "name_vn": "Giao thông",
        "name_en": "Transportation",
        "qml": "line/giao_thong.qml",
        "attr_hint": "",
    },
]

_POINT_STYLES = [
    {
        "id": "tram_truonghoc",
        "name_vn": "Trạm xá / Trường học",
        "name_en": "Health station / School",
        "qml": "point/tram_truonghoc.qml",
        "attr_hint": "Ten",
    },
    {
        "id": "nhan_tkhu",
        "name_vn": "Số hiệu tiểu khu / khoảnh / chủ rừng",
        "name_en": "Compartment / Sub-compartment / Owner labels",
        "qml": "point/nhan_tkhu.qml",
        "attr_hint": "ma",
    },
    {
        "id": "nhan_sodo",
        "name_vn": "Nhãn sơ đồ (tên xã, huyện)",
        "name_en": "Map labels (commune, district names)",
        "qml": "point/nhan_sodo.qml",
        "attr_hint": "ma",
    },
]


def _get_style_name(style):
    """Get localized style name."""
    lang = current_language()
    return style.get(f"name_{lang}", style.get("name_en", style["id"]))


def _get_style_desc(style):
    """Get localized style description."""
    lang = current_language()
    return style.get(f"description_{lang}", style.get("description_en", ""))


# =====================================================================
# Dialog
# =====================================================================

class TT16Dialog(QDialog):
    """Thematic Map dialog for TT 16/2023 LDLR styling."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("LVT4U — " + tr("Circular 16/2023"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(800, 600)
        self._master = _load_master()
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # Header
        hdr = QLabel("🎨  " + tr("Circular 16/2023") + " — LDLR Style Library")
        hdr.setFont(QFont("Arial", 14, QFont.Bold))
        hdr.setStyleSheet("color: #1565c0;")
        main_layout.addWidget(hdr)

        # Splitter: left = controls, right = colour preview
        splitter = QSplitter(Qt.Horizontal)

        # ---- LEFT PANEL: Controls ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)

        # 1. Layer selection
        grp_layer = QGroupBox(tr("Input layer"))
        form = QFormLayout(grp_layer)
        self.cmb_layer = QgsMapLayerComboBox()
        self.cmb_layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.cmb_layer.layerChanged.connect(self._on_layer_changed)
        form.addRow("Layer:", self.cmb_layer)

        self.lbl_geom = QLabel("")
        self.lbl_geom.setStyleSheet("color: #666; font-style: italic;")
        form.addRow("Geometry:", self.lbl_geom)
        left_layout.addWidget(grp_layer)

        # 2. Style selection
        grp_style = QGroupBox("Style")
        style_layout = QVBoxLayout(grp_style)

        self.cmb_style = QComboBox()
        self.cmb_style.setMinimumHeight(28)
        self.cmb_style.currentIndexChanged.connect(self._on_style_changed)
        style_layout.addWidget(self.cmb_style)

        self.lbl_style_desc = QLabel("")
        self.lbl_style_desc.setWordWrap(True)
        self.lbl_style_desc.setStyleSheet("color: #555; margin: 4px 0;")
        style_layout.addWidget(self.lbl_style_desc)

        # Field mapping
        field_row = QHBoxLayout()
        field_row.addWidget(QLabel(tr("Input layer") + " field:"))
        self.cmb_field = QgsFieldComboBox()
        field_row.addWidget(self.cmb_field)
        style_layout.addLayout(field_row)

        self.lbl_field_hint = QLabel("")
        self.lbl_field_hint.setStyleSheet("color: #888; font-size: 11px;")
        style_layout.addWidget(self.lbl_field_hint)

        left_layout.addWidget(grp_style)

        # 3. Apply button
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_apply = QPushButton("🎨  Apply Style")
        self.btn_apply.setFont(QFont("Arial", 11, QFont.Bold))
        self.btn_apply.setMinimumHeight(40)
        self.btn_apply.setMinimumWidth(180)
        self.btn_apply.setStyleSheet(
            "QPushButton { background: #1565c0; color: white; border-radius: 6px; padding: 8px 24px; }"
            "QPushButton:hover { background: #1976d2; }"
        )
        self.btn_apply.clicked.connect(self._apply_style)
        btn_row.addWidget(self.btn_apply)

        btn_close = QPushButton(tr("Close"))
        btn_close.setMinimumHeight(40)
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        btn_row.addStretch()
        left_layout.addLayout(btn_row)
        left_layout.addStretch()

        splitter.addWidget(left)

        # ---- RIGHT PANEL: Colour table ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        lbl_table = QLabel("📋  LDLR Colour Reference (93 codes)")
        lbl_table.setFont(QFont("Arial", 11, QFont.Bold))
        right_layout.addWidget(lbl_table)

        self.tbl_colours = QTableWidget()
        self.tbl_colours.setColumnCount(4)
        lang = current_language()
        if lang == "vi":
            self.tbl_colours.setHorizontalHeaderLabels(["Mã", "Màu", "Tên Việt", "HEX"])
        else:
            self.tbl_colours.setHorizontalHeaderLabels(["Code", "Colour", "Name (EN)", "HEX"])
        self.tbl_colours.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_colours.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_colours.setAlternatingRowColors(True)
        self.tbl_colours.verticalHeader().setDefaultSectionSize(22)
        self.tbl_colours.horizontalHeader().setStretchLastSection(True)
        self.tbl_colours.setColumnWidth(0, 70)
        self.tbl_colours.setColumnWidth(1, 40)
        self.tbl_colours.setColumnWidth(3, 75)
        self._populate_colour_table()
        right_layout.addWidget(self.tbl_colours)

        splitter.addWidget(right)
        splitter.setSizes([380, 420])

        main_layout.addWidget(splitter)

        # Init
        self._on_layer_changed(self.cmb_layer.currentLayer())

    # -----------------------------------------------------------------
    # Colour table
    # -----------------------------------------------------------------

    def _populate_colour_table(self):
        """Fill the reference colour table from master data."""
        codes = self._master["codes"]
        self.tbl_colours.setRowCount(len(codes))
        lang = current_language()

        for i, c in enumerate(codes):
            # Code
            item_code = QTableWidgetItem(c["code"])
            item_code.setTextAlignment(Qt.AlignCenter)
            self.tbl_colours.setItem(i, 0, item_code)

            # Colour swatch
            pixmap = QPixmap(24, 16)
            colour = QColor(c["hex"])
            pixmap.fill(colour)
            # Draw border
            painter = QPainter(pixmap)
            painter.setPen(QColor(100, 100, 100))
            painter.drawRect(0, 0, 23, 15)
            painter.end()

            item_colour = QTableWidgetItem()
            item_colour.setIcon(QIcon(pixmap))
            item_colour.setBackground(colour)
            self.tbl_colours.setItem(i, 1, item_colour)

            # Name
            name = c.get(f"name_{lang}", c.get("name_en", c["code"]))
            self.tbl_colours.setItem(i, 2, QTableWidgetItem(name))

            # HEX
            item_hex = QTableWidgetItem(c["hex"])
            item_hex.setTextAlignment(Qt.AlignCenter)
            self.tbl_colours.setItem(i, 3, item_hex)

    # -----------------------------------------------------------------
    # Events
    # -----------------------------------------------------------------

    def _on_layer_changed(self, layer):
        """Update UI when selected layer changes."""
        self.cmb_field.setLayer(layer)
        self._update_geometry_label(layer)
        self._update_style_list(layer)

    def _update_geometry_label(self, layer):
        """Show geometry type of selected layer."""
        if not layer or not isinstance(layer, QgsVectorLayer):
            self.lbl_geom.setText("—")
            return
        geom = layer.geometryType()
        names = {
            QgsWkbTypes.PointGeometry: "📍 Point",
            QgsWkbTypes.LineGeometry: "📏 Line",
            QgsWkbTypes.PolygonGeometry: "🔷 Polygon",
        }
        self.lbl_geom.setText(names.get(geom, "Unknown"))

    def _update_style_list(self, layer):
        """Populate style dropdown based on layer geometry type."""
        self.cmb_style.blockSignals(True)
        self.cmb_style.clear()

        if not layer or not isinstance(layer, QgsVectorLayer):
            self.cmb_style.blockSignals(False)
            return

        geom = layer.geometryType()
        if geom == QgsWkbTypes.PolygonGeometry:
            styles = _POLYGON_STYLES
        elif geom == QgsWkbTypes.LineGeometry:
            styles = _LINE_STYLES
        elif geom == QgsWkbTypes.PointGeometry:
            styles = _POINT_STYLES
        else:
            styles = []

        for s in styles:
            self.cmb_style.addItem(_get_style_name(s), s)

        self.cmb_style.blockSignals(False)
        if styles:
            self.cmb_style.setCurrentIndex(0)
            self._on_style_changed(0)

    def _on_style_changed(self, index):
        """Update description and field hint when style changes."""
        if index < 0:
            return
        style = self.cmb_style.itemData(index)
        if not style:
            return

        self.lbl_style_desc.setText(_get_style_desc(style))

        hint = style.get("attr_hint", "")
        if hint:
            self.lbl_field_hint.setText(
                f"💡 QML gốc dùng trường: \"{hint}\" — chọn trường tương ứng trong dữ liệu của bạn"
            )
            # Auto-select matching field if exists
            layer = self.cmb_layer.currentLayer()
            if layer:
                fields = [f.name() for f in layer.fields()]
                # Try exact match first, then case-insensitive
                for fname in fields:
                    if fname == hint:
                        self.cmb_field.setField(fname)
                        break
                    if fname.lower() == hint.lower():
                        self.cmb_field.setField(fname)
                        break
        else:
            self.lbl_field_hint.setText("")

    # -----------------------------------------------------------------
    # Apply
    # -----------------------------------------------------------------

    def _apply_style(self):
        """Apply the selected QML style to the current layer."""
        layer = self.cmb_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, "LVT4U", "Chọn layer trước!")
            return

        style = self.cmb_style.currentData()
        if not style:
            QMessageBox.warning(self, "LVT4U", "Chọn style!")
            return

        field_name = self.cmb_field.currentField()
        qml_path = os.path.join(_QML_DIR, style["qml"])

        if not os.path.isfile(qml_path):
            QMessageBox.critical(
                self, "LVT4U",
                f"QML file not found:\n{qml_path}"
            )
            return

        # Load QML
        msg, success = layer.loadNamedStyle(qml_path)

        if not success:
            QMessageBox.warning(
                self, "LVT4U",
                f"Failed to load style:\n{msg}"
            )
            return

        # Remap attribute if user chose a different field
        attr_hint = style.get("attr_hint", "")
        if field_name and attr_hint and field_name != attr_hint:
            self._remap_renderer_attribute(layer, field_name)

        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

        self.iface.messageBar().pushSuccess(
            "LVT4U",
            f"✅ Applied \"{_get_style_name(style)}\" → {layer.name()}"
        )

    def _remap_renderer_attribute(self, layer, new_field):
        """Change the renderer's classification attribute to user-selected field."""
        renderer = layer.renderer()
        if renderer is None:
            return

        rtype = renderer.type()
        if rtype == "categorizedSymbol":
            renderer.setClassAttribute(new_field)
        elif rtype == "graduatedSymbol":
            renderer.setClassAttribute(new_field)
        elif rtype == "mergedFeatureRenderer":
            embedded = renderer.embeddedRenderer()
            if embedded:
                if hasattr(embedded, 'setClassAttribute'):
                    embedded.setClassAttribute(new_field)

    def refresh_layers(self):
        """Refresh layer combo (called by menu launcher)."""
        pass
