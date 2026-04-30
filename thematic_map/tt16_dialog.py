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

from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtGui import QColor, QFont, QIcon, QPixmap, QPainter  # noqa: F811
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QAbstractItemView, QFrame,
    QTabWidget, QWidget,
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

        # Tabs
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # --- Tab 1: Apply Style + Plot Labels ---
        tab_main = QWidget()
        self.tabs.addTab(tab_main, "🎨 " + tr("Thematic Map"))
        self._build_main_tab(tab_main)

        # --- Tab 2: LDLR Reference ---
        tab_ref = QWidget()
        self.tabs.addTab(tab_ref, "📋 LDLR_Ref")
        self._build_ref_tab(tab_ref)

        # --- Tab 3: Legal Documents ---
        tab_legal = QWidget()
        self.tabs.addTab(tab_legal, "📜 " + tr("Legal Docs"))
        self._build_legal_tab(tab_legal)

        # Init
        self._on_layer_changed(self.cmb_layer.currentLayer())
        self._on_style_changed(self.cmb_style.currentIndex())

    def _build_main_tab(self, parent):
        ly = QVBoxLayout(parent)
        ly.setSpacing(8)

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

        ly.addLayout(top)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#ccc;")
        ly.addWidget(line)

        # Plot Labels header
        lbl_lh = QLabel("🏷️  " + tr("Plot Labels"))
        lbl_lh.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl_lh.setStyleSheet("color:#2e7d32; padding:2px 0;")
        ly.addWidget(lbl_lh)

        # Embed Plot Labels widget (stripped down)
        try:
            from .plot_labels import PlotLabelsDialog
            self._label_dlg = PlotLabelsDialog(self.iface, parent)
            self._label_dlg.setWindowFlags(Qt.Widget)
            # Hide redundant UI from embedded dialog
            self._label_dlg.btn_lang.setVisible(False)       # language toggle
            self._label_dlg.tabs.tabBar().setVisible(False)   # inner tab bar
            self._label_dlg.tabs.setCurrentIndex(0)           # show main tab
            self._label_dlg.grp_layer.setVisible(False)       # layer selector
            self._label_dlg.btn_apply.setVisible(False)       # apply button
            self._label_dlg.btn_export.setVisible(False)      # export button
            self._label_dlg.btn_reset.setVisible(False)       # reset button
            self._label_dlg.btn_save_cfg.setVisible(False)    # save cfg
            self._label_dlg.btn_load_cfg.setVisible(False)    # load cfg
            self._label_dlg.btn_close.setVisible(False)       # close button
            ly.addWidget(self._label_dlg, 1)
        except Exception as e:
            self._label_dlg = None
            ly.addWidget(QLabel(f"Plot Labels: {e}"))

        # Bottom action bar
        btn_row = QHBoxLayout()

        self.btn_apply = QPushButton("🎨  " + tr("Apply"))
        self.btn_apply.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_apply.setMinimumHeight(42)
        self.btn_apply.setStyleSheet(
            "QPushButton{background:#1565c0;color:white;border-radius:5px;"
            "padding:6px 20px;}"
            "QPushButton:hover{background:#1976d2;}"
        )
        self.btn_apply.clicked.connect(self._on_apply_all)
        btn_row.addWidget(self.btn_apply, 3)

        btn_close = QPushButton(tr("Close"))
        btn_close.setMinimumHeight(42)
        btn_close.setStyleSheet(
            "QPushButton{background:#757575;color:white;border-radius:5px;"
            "padding:6px 20px;}"
            "QPushButton:hover{background:#616161;}"
        )
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close, 1)

        ly.addLayout(btn_row)

    def _build_ref_tab(self, parent):
        ly = QVBoxLayout(parent)

        self.lbl_table = QLabel("📋  LDLR — 93 codes / 93 mã loại đất loại rừng")
        self.lbl_table.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_table.setStyleSheet("padding:2px 0;")
        ly.addWidget(self.lbl_table)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(6)
        self.tbl.setHorizontalHeaderLabels(
            ["LDLR", "Code", "Colour", "Tên (VN)", "Name (EN)", "HEX"]
        )
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setDefaultSectionSize(20)
        self.tbl.verticalHeader().setVisible(False)
        hh = self.tbl.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignLeft)
        self.tbl.setColumnWidth(0, 60)
        self.tbl.setColumnWidth(1, 42)
        self.tbl.setColumnWidth(2, 32)
        self.tbl.setColumnWidth(5, 72)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        ly.addWidget(self.tbl, 1)

        # Populate immediately
        self._populate_ref_table()

    def _populate_ref_table(self):
        """Fill the reference table with all 93 codes — bilingual."""
        codes = self._master["codes"]
        self.tbl.setRowCount(len(codes))

        for i, c in enumerate(codes):
            # Col 0: LDLR text code
            it0 = QTableWidgetItem(str(c.get("text_code", "")))
            it0.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(i, 0, it0)

            # Col 1: Numeric code
            it1 = QTableWidgetItem(str(c.get("num_code", "")))
            it1.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(i, 1, it1)

            # Col 2: Colour swatch
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
            self.tbl.setItem(i, 2, ci)

            # Col 3: Vietnamese name
            self.tbl.setItem(i, 3, QTableWidgetItem(
                c.get("name_vi", "")
            ))

            # Col 4: English name
            self.tbl.setItem(i, 4, QTableWidgetItem(
                c.get("name_en", "")
            ))

            # Col 5: HEX
            hi = QTableWidgetItem(c["hex"])
            hi.setTextAlignment(Qt.AlignCenter)
            hi.setForeground(QColor(100, 100, 100))
            self.tbl.setItem(i, 5, hi)

    # -----------------------------------------------------------------
    # Legal Documents tab
    # -----------------------------------------------------------------
    _LEGAL_DOCS = [
        {
            "file": "TT16_2023_BNN.pdf",
            "vi": "📄  Thông tư 16/2023/TT-BNNPTNT (bản ký)",
            "en": "📄  Circular 16/2023/TT-BNNPTNT (signed)",
            "desc_vi": "Quy định về trình tự, thủ tục phân loại đất, rừng",
            "desc_en": "Regulations on land and forest classification procedures",
        },
        {
            "file": "TT16_PhuLuc_45_46.doc",
            "vi": "📎  Phụ lục 45 + 46",
            "en": "📎  Appendix 45 + 46",
            "desc_vi": "Bảng phân loại đất, rừng (phần 1)",
            "desc_en": "Land and forest classification tables (part 1)",
        },
        {
            "file": "TT16_PhuLuc_47_48.doc",
            "vi": "📎  Phụ lục 47 + 48",
            "en": "📎  Appendix 47 + 48",
            "desc_vi": "Bảng phân loại đất, rừng (phần 2)",
            "desc_en": "Land and forest classification tables (part 2)",
        },
    ]

    def _build_legal_tab(self, parent):
        ly = QVBoxLayout(parent)
        ly.setSpacing(12)

        lang = current_language()
        hdr_text = (
            "📜  Văn bản pháp lý — Thông tư 16/2023"
            if lang == 'vi'
            else "📜  Legal Documents — Circular 16/2023"
        )
        lbl = QLabel(hdr_text)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl.setStyleSheet("color:#5d4037; padding:4px 0;")
        ly.addWidget(lbl)

        for doc in self._LEGAL_DOCS:
            row = QVBoxLayout()
            row.setSpacing(2)

            btn = QPushButton(doc[lang])
            btn.setFont(QFont("Segoe UI", 10))
            btn.setMinimumHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton{text-align:left;padding:6px 12px;"
                "background:#fff8e1;border:1px solid #ffe082;border-radius:4px;}"
                "QPushButton:hover{background:#fff3c4;border-color:#ffc107;}"
            )
            filepath = doc["file"]
            btn.clicked.connect(
                lambda checked, f=filepath: self._open_legal_doc(f)
            )
            row.addWidget(btn)

            desc = QLabel("    " + doc[f"desc_{lang}"])
            desc.setStyleSheet("color:#888; font-size:11px;")
            row.addWidget(desc)

            ly.addLayout(row)

        ly.addStretch()

        note_text = (
            "💡 Nhấn vào tài liệu để mở bằng ứng dụng mặc định"
            if lang == 'vi'
            else "💡 Click a document to open with default application"
        )
        note = QLabel(note_text)
        note.setStyleSheet("color:#aaa; font-size:10px; padding:4px;")
        ly.addWidget(note)

    def _open_legal_doc(self, filename):
        """Open a legal document with the system's default application."""
        docs_dir = os.path.join(os.path.dirname(__file__), os.pardir, "docs")
        filepath = os.path.normpath(os.path.join(docs_dir, filename))
        if os.path.isfile(filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
        else:
            QMessageBox.warning(
                self, "File not found",
                f"Cannot find: {filepath}"
            )

    # -----------------------------------------------------------------
    # Colour table — adapts to style type AND language (for Apply tab)
    # -----------------------------------------------------------------
    def _populate_table(self, style):
        """Update table header label when style changes (ref tab is static)."""
        # Ref tab is always bilingual — no need to rebuild
        pass

    # -----------------------------------------------------------------
    # Unified Apply — style + labels in one click
    # -----------------------------------------------------------------
    def _on_apply_all(self):
        """Apply thematic style AND plot labels in one operation."""
        # 1. Apply thematic categorized style
        self._on_apply_clicked()

        # 2. Apply labels from embedded PlotLabelsDialog
        if hasattr(self, '_label_dlg') and self._label_dlg is not None:
            # Sync layer: set the embedded dialog's layer to match TT16
            layer = self.cmb_layer.currentLayer()
            if layer:
                idx = self._label_dlg.cbo_layer.findText(layer.name())
                if idx >= 0:
                    self._label_dlg.cbo_layer.setCurrentIndex(idx)
            # Apply labels (uses overridden pure-label method)
            self._label_dlg._apply_to_layer()

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
    # Build ID — change this to verify correct code is loaded
    _BUILD = "v11-filter"

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

        from qgis.core import QgsMessageLog, Qgis
        _log = lambda m: QgsMessageLog.logMessage(
            f"[{self._BUILD}] {m}", "LVT4U", Qgis.Info
        )

        _log(f"Apply: style={style['id']}, field={field_name}")

        # ----------------------------------------------------------
        # Step 1: Load QML via QDomDocument (bypasses QGIS cache)
        # ----------------------------------------------------------
        from qgis.PyQt.QtXml import QDomDocument

        doc = QDomDocument()
        with open(qml_path, "r", encoding="utf-8") as f:
            content = f.read()
        xml_ok, xml_err, xml_line, xml_col = doc.setContent(content)
        if not xml_ok:
            QMessageBox.critical(
                self, "LVT4U",
                f"QML parse error at line {xml_line}:\n{xml_err}"
            )
            return

        # importNamedStyle returns (bool, str): (success, errorMsg)
        ok, err_msg = layer.importNamedStyle(doc)
        _log(f"importNamedStyle: ok={ok}, err='{err_msg}'")
        if not ok:
            QMessageBox.warning(self, "LVT4U", f"Import failed:\n{err_msg}")
            return

        # ----------------------------------------------------------
        # Step 2: Ensure classify attribute = user's field
        # ----------------------------------------------------------
        renderer = layer.renderer()
        _log(f"Renderer: {type(renderer).__name__}")

        from qgis.core import QgsCategorizedSymbolRenderer
        if not isinstance(renderer, QgsCategorizedSymbolRenderer):
            QMessageBox.warning(
                self, "LVT4U",
                f"Renderer is {type(renderer).__name__}, not categorized!"
            )
            return

        cur_attr = renderer.classAttribute()
        _log(f"QML classAttribute: '{cur_attr}', user field: '{field_name}'")

        # ALWAYS set the classify attribute to user's field
        renderer.setClassAttribute(field_name)
        _log(f"classAttribute set → '{renderer.classAttribute()}'")

        # ----------------------------------------------------------
        # Step 3: Scan data + filter categories
        # ----------------------------------------------------------
        idx = layer.fields().indexOf(field_name)
        _log(f"Field index: {idx}")
        if idx < 0:
            QMessageBox.warning(
                self, "LVT4U", f"Field '{field_name}' not found!"
            )
            return

        # Use QGIS native uniqueValues (most reliable)
        raw_unique = layer.uniqueValues(idx)
        _log(f"Raw unique values ({len(raw_unique)}): "
             f"{list(raw_unique)[:15]}")

        # Build normalized lookup set
        unique_vals = set()
        for rv in raw_unique:
            nv = self._normalize(rv)
            if nv:
                unique_vals.add(nv)

        _log(f"Normalized unique ({len(unique_vals)}): "
             f"{sorted(list(unique_vals))[:20]}")

        # Filter categories — keep only those with matching data
        cats = renderer.categories()
        total = len(cats)
        new_cats = []
        matched_vals = []
        skipped_vals = []
        for cat in cats:
            cv = cat.value()
            cn = self._normalize(cv)
            if cn and cn in unique_vals:
                new_cats.append(cat)
                matched_vals.append(cn)
            else:
                if cn:
                    skipped_vals.append(cn)

        _log(f"Matched ({len(new_cats)}): {matched_vals[:20]}")
        _log(f"Skipped ({len(skipped_vals)}): {skipped_vals[:10]}")
        _log(f"Filter: {total} → {len(new_cats)} kept")

        # Apply filtered renderer
        if new_cats:
            new_renderer = QgsCategorizedSymbolRenderer(
                field_name, new_cats
            )
            layer.setRenderer(new_renderer)
            _log("New filtered renderer applied")
        else:
            _log("WARNING: 0 matches — keeping all categories")

        # ----------------------------------------------------------
        # Step 4: Force complete refresh (aggressive)
        # ----------------------------------------------------------
        layer.emitStyleChanged()
        layer.triggerRepaint()

        try:
            from qgis.core import QgsProject
            tree_root = QgsProject.instance().layerTreeRoot()
            node = tree_root.findLayer(layer.id())
            if node:
                model = self.iface.layerTreeView().layerTreeModel()
                model.refreshLayerLegend(node)
        except Exception:
            self.iface.layerTreeView().refreshLayerSymbology(layer.id())

        self.iface.mapCanvas().refresh()

        self.iface.messageBar().pushSuccess(
            "LVT4U",
            f"✅ [{self._BUILD}] {_style_label(style)} → {layer.name()} "
            f"[{field_name}] — {len(new_cats)}/{total} categories"
        )

    @staticmethod
    def _normalize(val):
        """Normalize a value to a comparable string."""
        if val is None:
            return ""
        try:
            from qgis.core import NULL
            if val == NULL:
                return ""
        except ImportError:
            pass
        # Convert to string first, then try numeric normalization
        s = str(val).strip()
        if not s:
            return ""
        try:
            f = float(s)
            if f == int(f):
                return str(int(f))
            return str(f)
        except (ValueError, TypeError):
            return s

    # -----------------------------------------------------------------
    def refresh_layers(self):
        pass







