# -*- coding: utf-8 -*-
"""LVT Map Layout - Dialog UI built programmatically with PyQt5."""

import os
import math
from datetime import date

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QRadioButton, QButtonGroup, QGroupBox,
    QTextEdit, QPushButton, QProgressBar,
    QMessageBox, QGridLayout, QScrollArea
)
from qgis.core import QgsProject, QgsMapLayerProxyModel, QgsVectorLayer
from qgis.gui import QgsMapLayerComboBox

from .engine import LvtEngine


# Paper sizes in mm (width x height for landscape)
PAPER_SIZES = {
    # A-series (ISO 216)
    "A5 (210 × 148 mm)": (210, 148),
    "A4 (297 × 210 mm)": (297, 210),
    "A3 (420 × 297 mm)": (420, 297),
    "A2 (594 × 420 mm)": (594, 420),
    "A1 (841 × 594 mm)": (841, 594),
    "A0 (1189 × 841 mm)": (1189, 841),
    # B-series (ISO 216)
    "B5 (250 × 176 mm)": (250, 176),
    "B4 (353 × 250 mm)": (353, 250),
    "B3 (500 × 353 mm)": (500, 353),
    "B2 (707 × 500 mm)": (707, 500),
    "B1 (1000 × 707 mm)": (1000, 707),
    "B0 (1414 × 1000 mm)": (1414, 1000),
}

# Layout modes
MODE_SLIDE = "slide"
MODE_PRINT = "print"

# Standard scales for suggestion
STANDARD_SCALES = [
    500, 1000, 2000, 2500, 5000, 10000, 15000,
    20000, 25000, 50000, 100000, 250000, 500000, 1000000,
]


class LvtDialog(QDialog):
    """Main dialog for LVT Map Layout plugin."""

    CRS_LIST = [
        ("── WGS 84 ──", ""),
        ("EPSG:4326 — WGS 84 (Lat/Lon)", "EPSG:4326"),
        ("EPSG:32648 — WGS 84 / UTM 48N", "EPSG:32648"),
        ("EPSG:32649 — WGS 84 / UTM 49N", "EPSG:32649"),
        ("── VN-2000 Múi 6° ──", ""),
        ("EPSG:3405 — VN-2000 / UTM 48N", "EPSG:3405"),
        ("EPSG:3406 — VN-2000 / UTM 49N", "EPSG:3406"),
        ("── VN-2000 Múi 3° (34 tỉnh mới) ──", ""),
        ("103°00' — Điện Biên", "EPSG:9205"),
        ("104°00' — Sơn La", "EPSG:9206"),
        ("104°30' — Cà Mau", "EPSG:9207"),
        ("104°45' — An Giang, Lai Châu, Lào Cai, Nghệ An, Phú Thọ", "EPSG:9208"),
        ("105°00' — TP Hà Nội, Thanh Hóa, Ninh Bình, Đồng Tháp, TP Cần Thơ", "EPSG:5896"),
        ("105°30' — Hà Tĩnh, Hưng Yên, Vĩnh Long", "EPSG:9209"),
        ("105°45' — Cao Bằng, Tây Ninh, TP Hải Phòng, TP HCM", "EPSG:9210"),
        ("106°00' — Quảng Trị, Tuyên Quang", "EPSG:9211"),
        ("106°30' — Thái Nguyên", "EPSG:9213"),
        ("107°00' — Bắc Ninh, TP Huế", "EPSG:9214"),
        ("107°15' — Lạng Sơn", "EPSG:9215"),
        ("107°45' — Quảng Ninh, Đồng Nai, Lâm Đồng, TP Đà Nẵng", "EPSG:5899"),
        ("108°00' — Quảng Ngãi", "EPSG:9216"),
        ("108°15' — Gia Lai, Khánh Hòa", "EPSG:9217"),
        ("108°30' — Đắk Lắk", "EPSG:9218"),
    ]

    def __init__(self, iface, plugin_dir, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.engine = LvtEngine(iface, plugin_dir)
        self.setWindowTitle("LVT Map Layout")
        self.setMinimumSize(QSize(560, 500))
        self._build_ui()

    # ── UI Construction ──────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._tab_general(), "General")
        tabs.addTab(self._tab_map(), "Map Settings")
        tabs.addTab(self._tab_content(), "Content")
        root.addWidget(tabs)

        # Buttons
        btn_row = QHBoxLayout()

        btn_help = QPushButton("❓ Help")
        btn_help.setStyleSheet(
            "QPushButton{background:#ff8f00;color:#fff;font-weight:bold;"
            "padding:6px 14px;border-radius:4px}"
            "QPushButton:hover{background:#ffa000}"
        )
        btn_help.clicked.connect(self._show_help)

        self.btn_create = QPushButton("Create Layout / Tạo khung")
        self.btn_create.setStyleSheet(
            "QPushButton{background:#2e7d32;color:#fff;font-weight:bold;"
            "padding:6px 20px;border-radius:4px}"
            "QPushButton:hover{background:#388e3c}"
        )
        self.btn_create.clicked.connect(self._on_create)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)

        btn_row.addWidget(btn_help)

        btn_crs = QPushButton("🌐 CRS")
        btn_crs.setStyleSheet(
            "QPushButton{background:#1565c0;color:#fff;font-weight:bold;"
            "padding:6px 14px;border-radius:4px}"
            "QPushButton:hover{background:#1976d2}"
        )
        btn_crs.clicked.connect(self._show_crs)
        btn_row.addWidget(btn_crs)

        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        btn_row.addWidget(self.btn_create)
        root.addLayout(btn_row)

    # ── Tab: General ─────────────────────────────────────────────

    def _tab_general(self):
        w = QWidget()
        g = QGridLayout(w)
        row = 0

        # Layout mode selector
        g.addWidget(QLabel("Layout Mode / Chế độ:"), row, 0)
        mode_box = QHBoxLayout()
        self.rad_slide = QRadioButton("Slide (simple)")
        self.rad_print = QRadioButton("Print (full frame)")
        self.rad_slide.setChecked(True)
        bg_mode = QButtonGroup(w)
        bg_mode.addButton(self.rad_slide)
        bg_mode.addButton(self.rad_print)
        self.rad_slide.toggled.connect(self._toggle_mode_fields)
        mode_box.addWidget(self.rad_slide)
        mode_box.addWidget(self.rad_print)
        g.addLayout(mode_box, row, 1)
        row += 1

        # Language selector
        g.addWidget(QLabel("Language / Ngôn ngữ:"), row, 0)
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["English (EN)", "Tiếng Việt (VN)"])
        self.cmb_lang.setCurrentIndex(1)  # VN default
        g.addWidget(self.cmb_lang, row, 1)
        row += 1

        # ── Print-only fields ─────────────────────────────────────
        self.lbl_title = QLabel("Map Title / Tên bản đồ:")
        g.addWidget(self.lbl_title, row, 0)
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("e.g. Land Use Map 2026")
        g.addWidget(self.txt_title, row, 1)
        row += 1

        self.lbl_org = QLabel("Organization / Đơn vị:")
        g.addWidget(self.lbl_org, row, 0)
        self.txt_org = QLineEdit()
        self.txt_org.setPlaceholderText("e.g. Tan Cao Nguyên JSC")
        g.addWidget(self.txt_org, row, 1)
        row += 1

        self.lbl_study = QLabel("Study Area / Khu vực:")
        g.addWidget(self.lbl_study, row, 0)
        self.txt_study = QLineEdit()
        self.txt_study.setPlaceholderText("e.g. Gia Lai Province")
        g.addWidget(self.txt_study, row, 1)
        row += 1

        # References / Viện dẫn: fixed in template, not editable

        # Store print-only widgets for toggle
        self._print_widgets = [
            self.lbl_title, self.txt_title,
            self.lbl_org, self.txt_org,
            self.lbl_study, self.txt_study,
        ]
        for wgt in self._print_widgets:
            wgt.setVisible(False)  # hidden by default (Slide mode)

        # ── Common fields ─────────────────────────────────────────
        g.addWidget(QLabel("Author / Người lập:"), row, 0)
        self.txt_author = QLineEdit()
        self.txt_author.setPlaceholderText("e.g. Tác giả bản đồ / Author of Map")
        g.addWidget(self.txt_author, row, 1)
        row += 1

        g.addWidget(QLabel("Date / Ngày:"), row, 0)
        self.txt_date = QLineEdit(date.today().strftime("%d/%m/%Y"))
        g.addWidget(self.txt_date, row, 1)
        row += 1

        # ── Project CRS ──────────────────────────────────────────
        from qgis.core import QgsProject, QgsCoordinateReferenceSystem
        from qgis.PyQt.QtWidgets import QMessageBox

        cur_crs = QgsProject.instance().crs()
        self._crs_label = QLabel(
            f"📍 <b>{cur_crs.authid()}</b> — {cur_crs.description()}"
        )
        self._crs_label.setStyleSheet(
            "padding:4px 8px;border-radius:3px;"
            "font-size:11px;font-weight:bold;border:1px solid #999"
        )
        self._crs_label.setWordWrap(True)
        self._crs_label.setTextFormat(Qt.RichText)
        g.addWidget(QLabel("🌐 Project CRS:"), row, 0)
        g.addWidget(self._crs_label, row, 1)
        row += 1

        crs_row = QHBoxLayout()
        self.cmb_crs = QComboBox()
        self.cmb_crs.setMinimumWidth(280)
        for label, _ in self.CRS_LIST:
            self.cmb_crs.addItem(label)
        for i, (_, code) in enumerate(self.CRS_LIST):
            if not code:
                self.cmb_crs.model().item(i).setEnabled(False)
        # Pre-select
        for i, (_, code) in enumerate(self.CRS_LIST):
            if code == cur_crs.authid():
                self.cmb_crs.setCurrentIndex(i)
                break

        btn_apply_crs = QPushButton("✅ Apply")
        btn_apply_crs.setStyleSheet(
            "QPushButton{background:#2e7d32;color:#fff;font-weight:bold;"
            "padding:4px 12px;border-radius:3px}"
            "QPushButton:hover{background:#388e3c}"
        )

        def _apply_project_crs():
            idx = self.cmb_crs.currentIndex()
            code = self.CRS_LIST[idx][1]
            if not code:
                return
            new_crs = QgsCoordinateReferenceSystem(code)
            if not new_crs.isValid():
                QMessageBox.warning(self, "CRS Error", f"Invalid CRS: {code}")
                return
            QgsProject.instance().setCrs(new_crs)
            self._crs_label.setText(
                f"📍 <b>{new_crs.authid()}</b> — {new_crs.description()}"
            )

        btn_apply_crs.clicked.connect(_apply_project_crs)
        crs_row.addWidget(self.cmb_crs)
        crs_row.addWidget(btn_apply_crs)
        g.addWidget(QLabel("⚙️ Set CRS:"), row, 0)
        g.addLayout(crs_row, row, 1)
        row += 1

        g.setRowStretch(row, 1)
        return w

    def _toggle_mode_fields(self, checked):
        """Show/hide print-only fields based on mode selection."""
        is_print = self.rad_print.isChecked()
        for wgt in self._print_widgets:
            wgt.setVisible(is_print)

    # ── Tab: Map Settings ────────────────────────────────────────

    def _tab_map(self):
        w = QWidget()
        g = QGridLayout(w)
        row = 0

        g.addWidget(QLabel("Paper Size / Khổ giấy:"), row, 0)
        self.cmb_paper = QComboBox()
        self.cmb_paper.addItems(list(PAPER_SIZES.keys()) + ["Custom / Tự chọn"])
        self.cmb_paper.setCurrentIndex(1)  # A4 default
        self.cmb_paper.currentIndexChanged.connect(self._toggle_custom_size)
        g.addWidget(self.cmb_paper, row, 1)
        row += 1

        g.addWidget(QLabel("Custom Size (mm) / Kích thước tự chọn:"), row, 0)
        custom_box = QHBoxLayout()
        self.spn_custom_w = QSpinBox()
        self.spn_custom_w.setRange(50, 3000)
        self.spn_custom_w.setValue(297)
        self.spn_custom_w.setSuffix(" mm")
        self.spn_custom_w.setPrefix("W: ")
        self.spn_custom_w.setEnabled(False)
        self.spn_custom_h = QSpinBox()
        self.spn_custom_h.setRange(50, 3000)
        self.spn_custom_h.setValue(210)
        self.spn_custom_h.setSuffix(" mm")
        self.spn_custom_h.setPrefix("H: ")
        self.spn_custom_h.setEnabled(False)
        custom_box.addWidget(self.spn_custom_w)
        custom_box.addWidget(QLabel("×"))
        custom_box.addWidget(self.spn_custom_h)
        g.addLayout(custom_box, row, 1)
        row += 1

        # Draw Extent button (only enabled in Custom mode)
        self.btn_draw = QPushButton("🖊 Draw Extent / Vẽ phạm vi → tự tính kích thước")
        self.btn_draw.setStyleSheet(
            "QPushButton{background:#1565c0;color:#fff;font-weight:bold;"
            "padding:8px 16px;border-radius:4px;font-size:13px}"
            "QPushButton:hover{background:#1976d2}"
            "QPushButton:disabled{background:#bbb;color:#666}"
        )
        self.btn_draw.setEnabled(False)
        self.btn_draw.clicked.connect(self._on_draw_extent)
        g.addWidget(self.btn_draw, row, 0, 1, 2)
        row += 1

        # Drawn extent + scale suggestion display
        self.lbl_drawn = QLabel("")
        self.lbl_drawn.setStyleSheet("color:#888;font-style:italic")
        self.lbl_drawn.setWordWrap(True)
        g.addWidget(self.lbl_drawn, row, 0, 1, 2)
        row += 1

        # Orientation (hidden when Custom + Draw is used)
        self.lbl_orient = QLabel("Orientation / Hướng:")
        g.addWidget(self.lbl_orient, row, 0)
        orient_box = QHBoxLayout()
        self.rad_landscape = QRadioButton("Landscape / Ngang")
        self.rad_portrait = QRadioButton("Portrait / Dọc")
        self.rad_landscape.setChecked(True)
        bg = QButtonGroup(w)
        bg.addButton(self.rad_landscape)
        bg.addButton(self.rad_portrait)
        orient_box.addWidget(self.rad_landscape)
        orient_box.addWidget(self.rad_portrait)
        self.orient_widget = QWidget()
        self.orient_widget.setLayout(orient_box)
        g.addWidget(self.orient_widget, row, 1)
        row += 1

        # Scale
        g.addWidget(QLabel("Scale / Tỷ lệ:"), row, 0)
        scale_box = QHBoxLayout()
        self.chk_auto_scale = QCheckBox("Auto fit / Tự động")
        self.chk_auto_scale.setChecked(True)
        self.chk_auto_scale.stateChanged.connect(self._toggle_scale)
        self.spn_scale = QSpinBox()
        self.spn_scale.setRange(100, 10000000)
        self.spn_scale.setValue(10000)
        self.spn_scale.setPrefix("1 : ")
        self.spn_scale.setEnabled(False)
        self.spn_scale.valueChanged.connect(self._on_scale_changed)
        scale_box.addWidget(self.chk_auto_scale)
        scale_box.addWidget(self.spn_scale)
        g.addLayout(scale_box, row, 1)
        row += 1

        # Scale suggestion label
        self.lbl_scale_hint = QLabel("")
        self.lbl_scale_hint.setWordWrap(True)
        self.lbl_scale_hint.setStyleSheet(
            "color:#1565c0;font-style:italic;padding:2px 0"
        )
        g.addWidget(self.lbl_scale_hint, row, 0, 1, 2)
        row += 1

        g.setRowStretch(row, 1)
        return w

    # ── Tab: Content ─────────────────────────────────────────────

    def _tab_content(self):
        w = QWidget()
        g = QGridLayout(w)
        row = 0

        g.addWidget(QLabel("Nguồn dữ liệu xây dựng bản đồ:"), row, 0, 1, 2)
        row += 1
        self.txt_sources = QTextEdit()
        self.txt_sources.setPlaceholderText(
            "e.g. National land-use map 2020, Sentinel-2 imagery..."
        )
        self.txt_sources.setMaximumHeight(80)
        g.addWidget(self.txt_sources, row, 0, 1, 2)
        row += 1

        # Elements always shown (template-driven, no UI toggle needed)
        class _AlwaysTrue:
            def isChecked(self): return True
        class _DefaultArrow:
            def currentData(self): return ""
        self.chk_legend = _AlwaysTrue()
        self.chk_north = _AlwaysTrue()
        self.chk_scalebar = _AlwaysTrue()
        self.cmb_arrow = _DefaultArrow()

        g.setRowStretch(row, 1)
        return w

    # ── Slots ────────────────────────────────────────────────────


    def _toggle_custom_size(self, idx):
        is_custom = self.cmb_paper.currentText() == "Custom / Tự chọn"
        self.spn_custom_w.setEnabled(is_custom)
        self.spn_custom_h.setEnabled(is_custom)
        self.btn_draw.setEnabled(is_custom)
        # Show/hide orientation: hide when Custom (draw determines it)
        has_drawn = hasattr(self, "drawn_extent") and self.drawn_extent
        show_orient = not (is_custom and has_drawn)
        self.lbl_orient.setVisible(show_orient)
        self.orient_widget.setVisible(show_orient)
        if not is_custom:
            self.lbl_drawn.setText("")
            self.lbl_scale_hint.setText("")

    def _toggle_scale(self, state):
        self.spn_scale.setEnabled(state == Qt.Unchecked)
        if state == Qt.Unchecked and hasattr(self, 'drawn_extent') and self.drawn_extent:
            self._on_scale_changed(self.spn_scale.value())

    def refresh_layers(self):
        pass  # QgsMapLayerComboBox auto-refreshes

    # ── Draw Extent on Map ───────────────────────────────────────

    def _on_draw_extent(self):
        """Activate rectangle drawing tool on the map canvas."""
        from .extent_tool import LvtExtentTool
        canvas = self.iface.mapCanvas()
        self.extent_tool = LvtExtentTool(canvas, self._on_extent_drawn)
        canvas.setMapTool(self.extent_tool)
        self.iface.messageBar().pushInfo(
            "LVT", "Draw a rectangle on the map to define extent & page size."
        )
        self.hide()  # Hide dialog while drawing

    def _on_extent_drawn(self, rect):
        """Callback: store drawn extent and calculate initial page size.

        Workflow: draw extent → suggest scales → user picks scale → page auto-sizes.
        """
        self.drawn_extent = rect

        # Store extent in real-world meters
        crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        ext_w = rect.width()
        ext_h = rect.height()
        if crs.isGeographic():
            ext_w *= 111320
            ext_h *= 111320
        self._extent_w_m = ext_w
        self._extent_h_m = ext_h

        # Calculate natural scale from current canvas view
        canvas = self.iface.mapCanvas()
        mu_per_mm = canvas.mapUnitsPerPixel() * (canvas.logicalDpiX() / 25.4)
        view_map_w = rect.width() / mu_per_mm
        view_map_h = rect.height() / mu_per_mm
        natural_scale = max(
            ext_w / view_map_w * 1000 if view_map_w > 0 else 10000,
            ext_h / view_map_h * 1000 if view_map_h > 0 else 10000
        )

        # Suggest scales
        suggestions = [s for s in STANDARD_SCALES
                       if s >= natural_scale * 0.5 and s <= natural_scale * 3]
        if not suggestions:
            diffs = sorted([(abs(s - natural_scale), s) for s in STANDARD_SCALES])
            suggestions = [d[1] for d in diffs[:3]]
        suggestions.sort()
        suggestion_str = ", ".join([f"1:{s:,}" for s in suggestions])
        self.lbl_scale_hint.setText(
            f"💡 Suggested / Đề xuất: {suggestion_str}\n"
            f"   (Natural / Tự nhiên ≈ 1:{int(natural_scale):,})"
        )

        # Set best scale → triggers _on_scale_changed → sets page size
        best = min(STANDARD_SCALES, key=lambda s: abs(s - natural_scale))
        self.spn_scale.setValue(best)

        # Also calculate page for current scale right away
        self._recalc_page_from_scale(best)

        self.lbl_orient.setVisible(False)
        self.orient_widget.setVisible(False)

        self.show()
        self.raise_()

    def _on_scale_changed(self, scale_val):
        """When user changes scale, recalculate page size from drawn extent."""
        if not hasattr(self, '_extent_w_m') or not self._extent_w_m:
            return
        if self.chk_auto_scale.isChecked():
            return
        self._recalc_page_from_scale(scale_val)

    def _recalc_page_from_scale(self, scale_val):
        """Calculate page size from extent and scale.

        Uses size-dependent margins matching template design:
          A5/A4: left=19.15  top=32.65  bottom=30.9
          A3:    left=21.85  top=34.85  bottom=30.9
          A2:    left=25.85  top=59.85  bottom=30.9
          A1:    left=25.85  top=81.85  bottom=30.9
          A0:    left=35.85  top=99.85  bottom=30.9
        """
        if scale_val <= 0:
            return

        map_w_mm = self._extent_w_m / scale_val * 1000
        map_h_mm = self._extent_h_m / scale_val * 1000

        # Slide margins: 5mm all sides
        page_w = int(round(map_w_mm + 10))
        page_h = int(round(map_h_mm + 10))

        page_w = max(50, min(3000, page_w))
        page_h = max(50, min(3000, page_h))

        if page_w > 3000 or page_h > 3000:
            self.lbl_drawn.setStyleSheet("color:#c62828;font-weight:bold")
            self.lbl_drawn.setText(
                f"⚠️ Page too large! / Trang quá lớn! ({page_w}×{page_h} mm)\n"
                f"   Max 3000mm. Try a smaller scale / Thử tỷ lệ nhỏ hơn."
            )
            return

        self.spn_custom_w.setValue(page_w)
        self.spn_custom_h.setValue(page_h)

        if page_w >= page_h:
            self.rad_landscape.setChecked(True)
        else:
            self.rad_portrait.setChecked(True)

        self.lbl_drawn.setText(
            f"✅ Extent: {self.drawn_extent.xMinimum():.1f}, "
            f"{self.drawn_extent.yMinimum():.1f} → "
            f"{self.drawn_extent.xMaximum():.1f}, "
            f"{self.drawn_extent.yMaximum():.1f}\n"
            f"   Scale 1:{scale_val:,}  →  "
            f"Page: {page_w} × {page_h} mm  |  "
            f"Map: {int(map_w_mm)} × {int(map_h_mm)} mm"
        )
        self.lbl_drawn.setStyleSheet("color:#2e7d32;font-weight:bold")

    # ── Help ─────────────────────────────────────────────────────

    def _show_help(self):
        """Show help dialog with tabs: Plugin Guide + CRS Guide."""
        dlg = QDialog(self)
        dlg.setWindowTitle("📖 LVT Map Layout — Help / Trợ giúp")
        dlg.setMinimumSize(700, 560)
        lay = QVBoxLayout(dlg)

        # Language toggle
        btn_row = QHBoxLayout()
        btn_en = QPushButton("🇬🇧 English")
        btn_vn = QPushButton("🇻🇳 Tiếng Việt")
        for b in [btn_en, btn_vn]:
            b.setCheckable(True)
            b.setStyleSheet(
                "QPushButton{padding:6px 16px;border-radius:4px;"
                "font-weight:bold;border:2px solid #ccc}"
                "QPushButton:checked{background:#1565c0;color:#fff;border-color:#1565c0}"
            )
        btn_vn.setChecked(True)
        btn_row.addStretch()
        btn_row.addWidget(btn_en)
        btn_row.addWidget(btn_vn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # Tabbed content
        from qgis.PyQt.QtWidgets import QTabWidget
        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabWidget::pane{border:1px solid #ccc;border-radius:4px}"
            "QTabBar::tab{padding:8px 16px;font-weight:bold}"
            "QTabBar::tab:selected{background:#1565c0;color:#fff;"
            "border-radius:4px 4px 0 0}"
        )
        lay.addWidget(tabs)

        def _make_scroll():
            s = QScrollArea(); s.setWidgetResizable(True)
            l = QLabel(); l.setWordWrap(True)
            l.setTextFormat(Qt.RichText)
            l.setOpenExternalLinks(True); l.setMargin(12)
            s.setWidget(l); return s, l

        s1, lbl1 = _make_scroll()
        tabs.addTab(s1, "🗺️ Plugin Guide")

        s2, lbl2 = _make_scroll()
        tabs.addTab(s2, "🌐 CRS Guide")

        s3, lbl3 = _make_scroll()
        tabs.addTab(s3, "👤 Author / Tác giả")

        # Load content
        h_en, h_vn = self._help_text_en(), self._help_text_vn()
        c_en, c_vn = self._crs_guide_en(), self._crs_guide_vn()
        a_en, a_vn = self._author_text_en(), self._author_text_vn()
        lbl1.setText(h_vn); lbl2.setText(c_vn); lbl3.setText(a_vn)

        def switch_en():
            btn_en.setChecked(True); btn_vn.setChecked(False)
            lbl1.setText(h_en); lbl2.setText(c_en); lbl3.setText(a_en)
        def switch_vn():
            btn_vn.setChecked(True); btn_en.setChecked(False)
            lbl1.setText(h_vn); lbl2.setText(c_vn); lbl3.setText(a_vn)

        btn_en.clicked.connect(switch_en)
        btn_vn.clicked.connect(switch_vn)

        btn_close = QPushButton("OK")
        btn_close.clicked.connect(dlg.accept)
        lay.addWidget(btn_close)
        dlg.exec_()

    # ── CRS Library Dialog ───────────────────────────────────────

    def _show_crs(self):
        """Show CRS Library dialog with Set Project CRS feature."""
        from qgis.core import QgsProject, QgsCoordinateReferenceSystem
        from qgis.PyQt.QtWidgets import QComboBox, QMessageBox

        dlg = QDialog(self)
        dlg.setWindowTitle("🌐 CRS Library / Thư viện Hệ tọa độ")
        dlg.setMinimumSize(700, 560)
        lay = QVBoxLayout(dlg)

        # ── Current CRS info bar ──
        current_crs = QgsProject.instance().crs()
        crs_info = QLabel(
            f"📍 Current / Hiện tại: "
            f"<b>{current_crs.authid()}</b> — {current_crs.description()}"
        )
        crs_info.setStyleSheet(
            "padding:8px;border-radius:4px;"
            "font-size:12px;font-weight:bold;border:1px solid #999"
        )
        crs_info.setWordWrap(True)
        lay.addWidget(crs_info)

        # ── Set Project CRS ──
        set_row = QHBoxLayout()
        set_row.addWidget(QLabel("⚙️ <b>Set Project CRS / Đổi CRS dự án:</b>"))
        cmb_crs = QComboBox()
        cmb_crs.setMinimumWidth(340)
        for label, _ in self.CRS_LIST:
            cmb_crs.addItem(label)
        for i, (_, code) in enumerate(self.CRS_LIST):
            if not code:
                cmb_crs.model().item(i).setEnabled(False)

        cur_auth = current_crs.authid()
        for i, (_, code) in enumerate(self.CRS_LIST):
            if code == cur_auth:
                cmb_crs.setCurrentIndex(i)
                break

        btn_apply = QPushButton("✅ Apply / Áp dụng")
        btn_apply.setStyleSheet(
            "QPushButton{background:#2e7d32;color:#fff;font-weight:bold;"
            "padding:6px 16px;border-radius:4px}"
            "QPushButton:hover{background:#388e3c}"
        )

        def _apply_crs():
            idx = cmb_crs.currentIndex()
            code = self.CRS_LIST[idx][1]
            if not code:
                return
            new_crs = QgsCoordinateReferenceSystem(code)
            if not new_crs.isValid():
                QMessageBox.warning(dlg, "CRS Error",
                    f"Invalid CRS: {code}")
                return
            QgsProject.instance().setCrs(new_crs)
            crs_info.setText(
                f"📍 Current / Hiện tại: "
                f"<b>{new_crs.authid()}</b> — {new_crs.description()}"
            )
            # Sync General tab label
            if hasattr(self, '_crs_label'):
                self._crs_label.setText(
                    f"📍 <b>{new_crs.authid()}</b> — {new_crs.description()}"
                )
            QMessageBox.information(dlg, "✅ CRS Updated",
                f"Project CRS changed to:\n"
                f"{new_crs.authid()} — {new_crs.description()}")

        btn_apply.clicked.connect(_apply_crs)
        set_row.addWidget(cmb_crs)
        set_row.addWidget(btn_apply)
        lay.addLayout(set_row)

        # ── Language toggle ──
        btn_row = QHBoxLayout()
        btn_en = QPushButton("🇬🇧 English")
        btn_vn = QPushButton("🇻🇳 Tiếng Việt")
        for b in [btn_en, btn_vn]:
            b.setCheckable(True)
            b.setStyleSheet(
                "QPushButton{padding:6px 16px;border-radius:4px;"
                "font-weight:bold;border:2px solid #ccc}"
                "QPushButton:checked{background:#1565c0;color:#fff;border-color:#1565c0}"
            )
        btn_vn.setChecked(True)
        btn_row.addStretch()
        btn_row.addWidget(btn_en)
        btn_row.addWidget(btn_vn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # ── Tabbed CRS content ──
        tabs = QTabWidget()

        # --- Tab 1: CRS Library (34 provinces) ---
        scroll1 = QScrollArea()
        scroll1.setWidgetResizable(True)
        content = QLabel()
        content.setWordWrap(True)
        content.setTextFormat(Qt.RichText)
        content.setOpenExternalLinks(True)
        content.setMargin(12)
        scroll1.setWidget(content)
        tabs.addTab(scroll1, "🌐 CRS 34 Tỉnh Mới")

        # --- Tab 2: Legacy 63 provinces ---
        scroll2 = QScrollArea()
        scroll2.setWidgetResizable(True)
        legacy = QLabel()
        legacy.setWordWrap(True)
        legacy.setTextFormat(Qt.RichText)
        legacy.setOpenExternalLinks(True)
        legacy.setMargin(12)
        legacy.setText(self._crs_legacy_63())
        scroll2.setWidget(legacy)
        tabs.addTab(scroll2, "📋 63 Tỉnh Cũ (Tham khảo)")

        lay.addWidget(tabs)

        crs_en = self._crs_text_en()
        crs_vn = self._crs_text_vn()
        content.setText(crs_vn)

        def switch_en():
            btn_en.setChecked(True); btn_vn.setChecked(False)
            content.setText(crs_en)
        def switch_vn():
            btn_vn.setChecked(True); btn_en.setChecked(False)
            content.setText(crs_vn)

        btn_en.clicked.connect(switch_en)
        btn_vn.clicked.connect(switch_vn)

        btn_close = QPushButton("OK")
        btn_close.clicked.connect(dlg.accept)
        lay.addWidget(btn_close)
        dlg.exec_()

    def _help_text_en(self):
        return """
<h2>🗺️ LVT Map Layout v2.0 — User Guide</h2>

<h3>🔷 LAYOUT MODES</h3>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;margin-bottom:8px">
<tr style="background:#e3f2fd"><td><b>🖼️ Slide</b></td>
<td>Simple, borderless layout — ideal for presentations, reports, quick exports.</td></tr>
<tr style="background:#e8f5e9"><td><b>🖨️ Print</b></td>
<td>Full cartographic layout — multi-line frame, coordinate grids, scalebars,
title block, references. Professional map output (A5→A0).</td></tr>
</table>

<h3>📌 Step 1 — General Settings</h3>
<ul>
<li>🔘 <b>Layout Mode:</b> Choose <b>Slide</b> or <b>Print</b>.</li>
<li>🌐 <b>Language:</b> EN (English) or VN (Tiếng Việt) — controls all template labels.</li>
</ul>
<p><b>🖨️ Print mode — additional fields:</b></p>
<ul>
<li>📝 <b>Map Title:</b> Main title displayed in the title block.</li>
<li>🏢 <b>Organization:</b> Company / organization name.</li>
<li>📍 <b>Study Area:</b> Geographic area name (province, district, etc.).</li>
<li>📚 <b>References:</b> Technical standards, e.g. <i>TCVN 8211:2009</i>.</li>
</ul>
<p><b>👤 Common fields (both modes):</b></p>
<ul>
<li>✍️ <b>Author:</b> Map creator name.</li>
<li>📅 <b>Date:</b> Creation date (auto-filled today).</li>
</ul>

<h3>📌 Step 2 — Map Settings</h3>
<p><b>📐 Option A — Standard Paper:</b></p>
<ul>
<li>📄 Select paper size: <b>A5, A4, A3, A2, A1, A0</b>.</li>
<li>🔄 Choose orientation: <b>Landscape</b> (horizontal) or <b>Portrait</b> (vertical).</li>
<li>Map extent = current QGIS canvas view.</li>
</ul>
<p><b>🖊️ Option B — Draw Extent (Custom):</b></p>
<ol>
<li>Select <b>"Custom / Tự chọn"</b> in Paper Size dropdown.</li>
<li>Click <b>"🖊 Draw Extent"</b> button → draw a rectangle on the map canvas.</li>
<li>The drawn rectangle defines the exact map content area.</li>
<li>Plugin auto-calculates page dimensions and suggests standard scales.</li>
<li>💡 Scale suggestions appear below (e.g. 1:5,000 / 1:10,000 / 1:25,000).</li>
</ol>
<p><b>🔍 Scale options:</b></p>
<ul>
<li>☑ <b>Auto fit:</b> Scale adjusts automatically to fill the page.</li>
<li>☐ <b>Manual:</b> Uncheck "Auto fit" → enter a specific scale (e.g. 1:10,000).</li>
</ul>

<h3>📌 Step 3 — Content</h3>
<ul>
<li>📋 <b>Data Sources:</b> List your map data sources (satellite imagery, survey data, etc.).</li>
<li>🧭 <b>North Arrow:</b> Toggle on/off.</li>
<li>📏 <b>Scale Bar:</b> Toggle on/off (meter + degree/minute bars in Print mode).</li>
<li>🗂️ <b>Legend:</b> Toggle on/off.</li>
</ul>

<h3>📌 Step 4 — Create &amp; Export</h3>
<ol>
<li>✅ Click <b>"Create Layout / Tạo khung"</b>.</li>
<li>🖥️ Layout opens in <b>QGIS Layout Designer</b>.</li>
<li>👀 Review all elements — adjust if needed.</li>
<li>💾 <b>File → Export as PDF</b> or <b>Export as Image</b> (PNG/TIFF).</li>
</ol>

<h3>📄 Paper Size Reference (ISO 216)</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px">
<tr style="background:#f5f5f5"><th>Size</th><th>Dimensions (mm)</th><th>Best for</th></tr>
<tr style="background:#e3f2fd"><td colspan="3"><b>A-series</b></td></tr>
<tr><td>A5</td><td>210 × 148</td><td>Field pocket maps</td></tr>
<tr><td>A4</td><td>297 × 210</td><td>Reports, desk reference</td></tr>
<tr><td>A3</td><td>420 × 297</td><td>Field operations, presentations</td></tr>
<tr><td>A2</td><td>594 × 420</td><td>Wall display, planning</td></tr>
<tr><td>A1</td><td>841 × 594</td><td>Large wall maps</td></tr>
<tr><td>A0</td><td>1189 × 841</td><td>Exhibition, official submissions</td></tr>
<tr style="background:#e8f5e9"><td colspan="3"><b>B-series</b> (larger than A at same number)</td></tr>
<tr><td>B5</td><td>250 × 176</td><td>Books, envelopes</td></tr>
<tr><td>B4</td><td>353 × 250</td><td>Newspapers, atlases</td></tr>
<tr><td>B3</td><td>500 × 353</td><td>Posters, large charts</td></tr>
<tr><td>B2</td><td>707 × 500</td><td>Large posters, wall maps</td></tr>
<tr><td>B1</td><td>1000 × 707</td><td>Very large wall displays</td></tr>
<tr><td>B0</td><td>1414 × 1000</td><td>Exhibition, architectural plans</td></tr>
</table>

<p style="color:#888;font-size:10px;margin-top:12px"><i>LVT Map Layout v2.0 — Designed for forestry &amp; environmental mapping.</i></p>"""

    def _help_text_vn(self):
        return """
<h2>🗺️ LVT Map Layout v2.0 — Hướng dẫn sử dụng</h2>

<h3>🔷 CHẾ ĐỘ KHUNG BẢN ĐỒ</h3>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;margin-bottom:8px">
<tr style="background:#e3f2fd"><td><b>🖼️ Slide</b></td>
<td>Khung đơn giản, không viền — phù hợp trình chiếu, báo cáo, xuất nhanh.</td></tr>
<tr style="background:#e8f5e9"><td><b>🖨️ Print</b></td>
<td>Khung bản đồ chuyên nghiệp — khung viền nhiều lớp, lưới tọa độ,
thước tỷ lệ, khối tiêu đề, viện dẫn. Xuất bản đồ chuẩn (A5→A0).</td></tr>
</table>

<h3>📌 Bước 1 — Thiết lập chung (Tab General)</h3>
<ul>
<li>🔘 <b>Chế độ:</b> Chọn <b>Slide</b> hoặc <b>Print</b>.</li>
<li>🌐 <b>Ngôn ngữ:</b> EN (Tiếng Anh) hoặc VN (Tiếng Việt) — thay đổi toàn bộ nhãn trong khung.</li>
</ul>
<p><b>🖨️ Chế độ Print — các trường bổ sung:</b></p>
<ul>
<li>📝 <b>Tên bản đồ:</b> Tiêu đề chính hiển thị trong khối tiêu đề.</li>
<li>🏢 <b>Đơn vị:</b> Tên công ty / tổ chức xây dựng bản đồ.</li>
<li>📍 <b>Khu vực:</b> Tên khu vực nghiên cứu (tỉnh, huyện, xã, v.v.).</li>
<li>📚 <b>Viện dẫn:</b> Tiêu chuẩn kỹ thuật, vd: <i>TCVN 8211:2009</i>.</li>
</ul>
<p><b>👤 Trường chung (cả hai chế độ):</b></p>
<ul>
<li>✍️ <b>Người lập:</b> Tên người tạo bản đồ.</li>
<li>📅 <b>Ngày:</b> Ngày lập (tự điền ngày hôm nay).</li>
</ul>

<h3>📌 Bước 2 — Thiết lập bản đồ (Tab Map Settings)</h3>
<p><b>📐 Cách 1 — Khổ giấy chuẩn:</b></p>
<ul>
<li>📄 Chọn khổ giấy: <b>A5, A4, A3, A2, A1, A0</b>.</li>
<li>🔄 Chọn hướng: <b>Ngang</b> (Landscape) hoặc <b>Dọc</b> (Portrait).</li>
<li>Phạm vi bản đồ = toàn bộ canvas QGIS hiện tại.</li>
</ul>
<p><b>🖊️ Cách 2 — Vẽ phạm vi (Custom):</b></p>
<ol>
<li>Chọn <b>"Custom / Tự chọn"</b> ở dropdown Khổ giấy.</li>
<li>Bấm nút <b>"🖊 Draw Extent"</b> → vẽ hình chữ nhật trên bản đồ.</li>
<li>Hình chữ nhật vẽ = vùng nội dung bản đồ chính xác.</li>
<li>Plugin tự tính kích thước trang và đề xuất tỷ lệ chuẩn.</li>
<li>💡 Các tỷ lệ đề xuất hiện bên dưới (vd: 1:5.000 / 1:10.000 / 1:25.000).</li>
</ol>
<p><b>🔍 Tùy chọn tỷ lệ:</b></p>
<ul>
<li>☑ <b>Auto fit:</b> Tỷ lệ tự động điều chỉnh vừa trang.</li>
<li>☐ <b>Tự chọn:</b> Bỏ dấu "Auto fit" → nhập tỷ lệ cụ thể (vd: 1:10.000).</li>
</ul>

<h3>📌 Bước 3 — Nội dung (Tab Content)</h3>
<ul>
<li>📋 <b>Nguồn dữ liệu:</b> Liệt kê các nguồn dữ liệu bản đồ (ảnh vệ tinh, khảo sát, v.v.).</li>
<li>🧭 <b>Mũi tên Bắc:</b> Bật/tắt.</li>
<li>📏 <b>Thước tỷ lệ:</b> Bật/tắt (thước mét + thước độ/phút ở chế độ Print).</li>
<li>🗂️ <b>Chú giải:</b> Bật/tắt.</li>
</ul>

<h3>📌 Bước 4 — Tạo &amp; Xuất bản đồ</h3>
<ol>
<li>✅ Bấm <b>"Create Layout / Tạo khung"</b>.</li>
<li>🖥️ Khung bản đồ mở trong <b>QGIS Layout Designer</b>.</li>
<li>👀 Kiểm tra các thành phần — chỉnh sửa nếu cần.</li>
<li>💾 <b>File → Export as PDF</b> hoặc <b>Export as Image</b> (PNG/TIFF).</li>
</ol>

<h3>📄 Bảng khổ giấy tham khảo (ISO 216)</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px">
<tr style="background:#f5f5f5"><th>Khổ</th><th>Kích thước (mm)</th><th>Phù hợp cho</th></tr>
<tr style="background:#e3f2fd"><td colspan="3"><b>Dòng A</b></td></tr>
<tr><td>A5</td><td>210 × 148</td><td>Bản đồ bỏ túi, thực địa</td></tr>
<tr><td>A4</td><td>297 × 210</td><td>Báo cáo, tài liệu tham khảo</td></tr>
<tr><td>A3</td><td>420 × 297</td><td>Thực địa, trình bày</td></tr>
<tr><td>A2</td><td>594 × 420</td><td>Treo tường, quy hoạch</td></tr>
<tr><td>A1</td><td>841 × 594</td><td>Bản đồ treo tường lớn</td></tr>
<tr><td>A0</td><td>1189 × 841</td><td>Triển lãm, nộp hồ sơ chính thức</td></tr>
<tr style="background:#e8f5e9"><td colspan="3"><b>Dòng B</b> (lớn hơn A cùng số)</td></tr>
<tr><td>B5</td><td>250 × 176</td><td>Sách, bìa thư</td></tr>
<tr><td>B4</td><td>353 × 250</td><td>Báo, tập bản đồ</td></tr>
<tr><td>B3</td><td>500 × 353</td><td>Poster, biểu đồ lớn</td></tr>
<tr><td>B2</td><td>707 × 500</td><td>Poster lớn, bản đồ treo tường</td></tr>
<tr><td>B1</td><td>1000 × 707</td><td>Trưng bày cỡ rất lớn</td></tr>
<tr><td>B0</td><td>1414 × 1000</td><td>Triển lãm, bản vẽ kiến trúc</td></tr>
</table>

<p style="color:#888;font-size:10px;margin-top:12px"><i>LVT Map Layout v2.0 — Thiết kế cho bản đồ lâm nghiệp &amp; môi trường.</i></p>"""


    # ── Author Text ───────────────────────────────────────────────

    def _author_text_en(self):
        return """
<div style="text-align:center;padding:16px">
<h2>👨‍💻 Lộc Vũ Trung</h2>
<p style="font-size:13px;color:#555">GIS & Forestry Technology Specialist</p>
</div>

<table border="0" cellpadding="8" cellspacing="0" style="width:100%;font-size:12px">
<tr style="background:#e3f2fd;border-radius:4px">
<td width="30%">📱 <b>Zalo:</b></td><td>0913 191 178</td></tr>
<tr style="background:#f5f5f5">
<td>🌐 <b>Website:</b></td>
<td><a href="http://locvutrung.lvtcenter.it.com">locvutrung.lvtcenter.it.com</a></td></tr>
<tr style="background:#e3f2fd">
<td>▶️ <b>YouTube:</b></td>
<td><a href="https://www.youtube.com/@locvutrung">youtube.com/@locvutrung</a></td></tr>
</table>

<h3 style="margin-top:16px">🎯 Expertise</h3>
<table border="0" cellpadding="6" cellspacing="4" style="font-size:11px">
<tr>
<td style="background:#e8f5e9;border-radius:4px;padding:6px 12px">🌲 <b>FSC/CoC</b></td>
<td style="background:#e3f2fd;border-radius:4px;padding:6px 12px">🇲🇺 <b>EUDR</b></td>
<td style="background:#fff3e0;border-radius:4px;padding:6px 12px">🗺️ <b>QGIS</b></td>
<td style="background:#fce4ec;border-radius:4px;padding:6px 12px">📊 <b>DATA</b></td>
</tr>
<tr>
<td style="background:#f3e5f5;border-radius:4px;padding:6px 12px">🌐 <b>Webapp</b></td>
<td style="background:#e8eaf6;border-radius:4px;padding:6px 12px">📱 <b>Appsheet</b></td>
<td style="background:#e0f2f1;border-radius:4px;padding:6px 12px" colspan="2">🌳 <b>Silviculture</b></td>
</tr>
</table>

<hr>
<p style="color:#888;font-size:10px;text-align:center;margin-top:12px">
<i>LVT Map Layout v2.0 — Designed for forestry & environmental mapping.</i>
</p>"""

    def _author_text_vn(self):
        return """
<div style="text-align:center;padding:16px">
<h2>👨‍💻 Lộc Vũ Trung</h2>
<p style="font-size:13px;color:#555">Chuyên gia Công nghệ GIS & Lâm nghiệp</p>
</div>

<table border="0" cellpadding="8" cellspacing="0" style="width:100%;font-size:12px">
<tr style="background:#e3f2fd;border-radius:4px">
<td width="30%">📱 <b>Zalo:</b></td><td>0913 191 178</td></tr>
<tr style="background:#f5f5f5">
<td>🌐 <b>Website:</b></td>
<td><a href="http://locvutrung.lvtcenter.it.com">locvutrung.lvtcenter.it.com</a></td></tr>
<tr style="background:#e3f2fd">
<td>▶️ <b>YouTube:</b></td>
<td><a href="https://www.youtube.com/@locvutrung">youtube.com/@locvutrung</a></td></tr>
</table>

<h3 style="margin-top:16px">🎯 Phạm vi chuyên môn</h3>
<table border="0" cellpadding="6" cellspacing="4" style="font-size:11px">
<tr>
<td style="background:#e8f5e9;border-radius:4px;padding:6px 12px">🌲 <b>FSC/CoC</b></td>
<td style="background:#e3f2fd;border-radius:4px;padding:6px 12px">🇲🇺 <b>EUDR</b></td>
<td style="background:#fff3e0;border-radius:4px;padding:6px 12px">🗺️ <b>QGIS</b></td>
<td style="background:#fce4ec;border-radius:4px;padding:6px 12px">📊 <b>DATA</b></td>
</tr>
<tr>
<td style="background:#f3e5f5;border-radius:4px;padding:6px 12px">🌐 <b>Webapp</b></td>
<td style="background:#e8eaf6;border-radius:4px;padding:6px 12px">📱 <b>Appsheet</b></td>
<td style="background:#e0f2f1;border-radius:4px;padding:6px 12px" colspan="2">🌳 <b>Lâm sinh</b></td>
</tr>
</table>

<hr>
<p style="color:#888;font-size:10px;text-align:center;margin-top:12px">
<i>LVT Map Layout v2.0 — Thiết kế cho bản đồ lâm nghiệp & môi trường.</i>
</p>"""

    # ── CRS Library Text ─────────────────────────────────────────

    def _crs_text_en(self):
        return """
<h2>🌐 CRS Library — Coordinate Reference Systems for Vietnam</h2>
<p>Quick reference for EPSG codes commonly used in forestry & environmental mapping in Vietnam.</p>

<h3>🔵 Global / WGS 84</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#e3f2fd"><th>EPSG</th><th>Name</th><th>Type</th><th>Description</th></tr>
<tr><td><b>4326</b></td><td>WGS 84</td><td>Geographic</td><td>Global standard (GPS). Lat/Lon in degrees. Used by Google Earth, OpenStreetMap.</td></tr>
<tr><td><b>32648</b></td><td>WGS 84 / UTM zone 48N</td><td>Projected</td><td>Western Vietnam (west of 108°E). Meters. Good for area calculations.</td></tr>
<tr><td><b>32649</b></td><td>WGS 84 / UTM zone 49N</td><td>Projected</td><td>Eastern Vietnam (east of 108°E). Meters.</td></tr>
</table>

<h3>🟢 VN-2000 — National 6° Zones (Toàn quốc)</h3>
<p>Used for national-scale mapping. Based on WGS 84 ellipsoid, Transverse Mercator projection.</p>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#e8f5e9"><th>EPSG</th><th>Name</th><th>Central Meridian</th><th>Coverage</th></tr>
<tr><td><b>3405</b></td><td>VN-2000 / UTM zone 48N</td><td>105°E</td><td>Western Vietnam (west of 108°E)</td></tr>
<tr><td><b>3406</b></td><td>VN-2000 / UTM zone 49N</td><td>111°E</td><td>Eastern Vietnam (east of 108°E)</td></tr>
</table>

<h3>🟡 VN-2000 — Provincial 3° Zones (Tỉnh)</h3>
<p>Used for large-scale cadastral & engineering mapping. Each province is assigned a specific central meridian.</p>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#fff9c4"><th>CM</th><th>Province (New Name)</th><th>Merged From</th></tr>
<tr><td><b>103°00'</b></td><td>Điện Biên</td><td>—</td></tr>
<tr><td><b>104°00'</b></td><td>Sơn La</td><td>—</td></tr>
<tr><td><b>104°30'</b></td><td>Cà Mau</td><td>Bạc Liêu + Cà Mau</td></tr>
<tr><td rowspan="5"><b>104°45'</b></td><td>An Giang</td><td>Kiên Giang + An Giang</td></tr>
<tr><td>Lai Châu</td><td>—</td></tr>
<tr><td>Lào Cai</td><td>Lào Cai + Yên Bái</td></tr>
<tr><td>Nghệ An</td><td>—</td></tr>
<tr><td>Phú Thọ</td><td>Hòa Bình + Vĩnh Phúc + Phú Thọ</td></tr>
<tr><td rowspan="5"><b>105°00'</b></td><td>TP Hà Nội</td><td>—</td></tr>
<tr><td>Thanh Hóa</td><td>—</td></tr>
<tr><td>Ninh Bình</td><td>Hà Nam + Nam Định + Ninh Bình</td></tr>
<tr><td>Đồng Tháp</td><td>Tiền Giang + Đồng Tháp</td></tr>
<tr><td>TP Cần Thơ</td><td>Sóc Trăng + Hậu Giang + TP Cần Thơ</td></tr>
<tr><td rowspan="3"><b>105°30'</b></td><td>Hà Tĩnh</td><td>—</td></tr>
<tr><td>Hưng Yên</td><td>Hưng Yên + Thái Bình</td></tr>
<tr><td>Vĩnh Long</td><td>Bến Tre + Vĩnh Long + Trà Vinh</td></tr>
<tr><td rowspan="4"><b>105°45'</b></td><td>Cao Bằng</td><td>—</td></tr>
<tr><td>Tây Ninh</td><td>Tây Ninh + Long An</td></tr>
<tr><td>TP Hải Phòng</td><td>TP Hải Phòng + Hải Dương</td></tr>
<tr><td>TP HCM</td><td>Bà Rịa-VT + Bình Dương + TP HCM</td></tr>
<tr><td rowspan="2"><b>106°00'</b></td><td>Quảng Trị</td><td>Quảng Bình + Quảng Trị</td></tr>
<tr><td>Tuyên Quang</td><td>Hà Giang + Tuyên Quang</td></tr>
<tr><td><b>106°30'</b></td><td>Thái Nguyên</td><td>Thái Nguyên + Bắc Kạn</td></tr>
<tr><td rowspan="2"><b>107°00'</b></td><td>Bắc Ninh</td><td>Bắc Ninh + Bắc Giang</td></tr>
<tr><td>TP Huế</td><td>—</td></tr>
<tr><td><b>107°15'</b></td><td>Lạng Sơn</td><td>—</td></tr>
<tr><td rowspan="4"><b>107°45'</b></td><td>Quảng Ninh</td><td>—</td></tr>
<tr><td>Đồng Nai</td><td>Bình Phước + Đồng Nai</td></tr>
<tr><td>Lâm Đồng</td><td>Đắk Nông + Bình Thuận + Lâm Đồng</td></tr>
<tr><td>TP Đà Nẵng</td><td>Quảng Nam + TP Đà Nẵng</td></tr>
<tr><td><b>108°00'</b></td><td>Quảng Ngãi</td><td>Kon Tum + Quảng Ngãi</td></tr>
<tr><td rowspan="2"><b>108°15'</b></td><td>Gia Lai</td><td>Gia Lai + Bình Định</td></tr>
<tr><td>Khánh Hòa</td><td>Ninh Thuận + Khánh Hòa</td></tr>
<tr><td><b>108°30'</b></td><td>Đắk Lắk</td><td>Phú Yên + Đắk Lắk</td></tr>
</table>

<h3>💡 How to Choose?</h3>
<ul>
<li>📍 <b>GPS / web mapping:</b> EPSG:4326 (WGS 84)</li>
<li>📐 <b>Area/distance calculations:</b> EPSG:32648 or 32649 (UTM)</li>
<li>🗺️ <b>National maps:</b> EPSG:3405 or 3406 (VN-2000 / 6°)</li>
<li>📏 <b>Cadastral / provincial:</b> Use the 3° zone matching your province</li>
</ul>
<p style="color:#888;font-size:10px"><i>Source: EPSG Registry (epsg.io) — MONRE Vietnam</i></p>"""

    def _crs_text_vn(self):
        return """
<h2>🌐 Thư viện Hệ tọa độ — CRS cho Việt Nam</h2>
<p>Tra cứu nhanh mã EPSG thường dùng trong lâm nghiệp & môi trường tại Việt Nam.</p>

<h3>🔵 Toàn cầu / WGS 84</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#e3f2fd"><th>EPSG</th><th>Tên</th><th>Loại</th><th>Mô tả</th></tr>
<tr><td><b>4326</b></td><td>WGS 84</td><td>Địa lý</td><td>Tiêu chuẩn toàn cầu (GPS). Tọa độ Lat/Lon tính bằng độ. Google Earth, OpenStreetMap.</td></tr>
<tr><td><b>32648</b></td><td>WGS 84 / UTM zone 48N</td><td>Phép chiếu</td><td>Tây Việt Nam (phía tây 108°E). Đơn vị: mét.</td></tr>
<tr><td><b>32649</b></td><td>WGS 84 / UTM zone 49N</td><td>Phép chiếu</td><td>Đông Việt Nam (phía đông 108°E). Đơn vị: mét.</td></tr>
</table>

<h3>🟢 VN-2000 — Múi 6° (Toàn quốc)</h3>
<p>Dùng cho bản đồ quy mô quốc gia. Dựa trên ellipsoid WGS 84, phép chiếu Transverse Mercator.</p>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#e8f5e9"><th>EPSG</th><th>Tên</th><th>Kinh tuyến trục</th><th>Phạm vi</th></tr>
<tr><td><b>3405</b></td><td>VN-2000 / UTM zone 48N</td><td>105°E</td><td>Tây Việt Nam (phía tây 108°E)</td></tr>
<tr><td><b>3406</b></td><td>VN-2000 / UTM zone 49N</td><td>111°E</td><td>Đông Việt Nam (phía đông 108°E)</td></tr>
</table>

<h3>🟡 VN-2000 — Múi 3° (Tỉnh)</h3>
<p>Dùng cho bản đồ địa chính & kỹ thuật tỷ lệ lớn. Mỗi tỉnh được gán một kinh tuyến trục riêng.</p>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#fff9c4"><th>KTT</th><th>Tỉnh (tên mới)</th><th>Sáp nhập từ</th></tr>
<tr><td><b>103°00'</b></td><td>Điện Biên</td><td>—</td></tr>
<tr><td><b>104°00'</b></td><td>Sơn La</td><td>—</td></tr>
<tr><td><b>104°30'</b></td><td>Cà Mau</td><td>Bạc Liêu + Cà Mau</td></tr>
<tr><td rowspan="5"><b>104°45'</b></td><td>An Giang</td><td>Kiên Giang + An Giang</td></tr>
<tr><td>Lai Châu</td><td>—</td></tr>
<tr><td>Lào Cai</td><td>Lào Cai + Yên Bái</td></tr>
<tr><td>Nghệ An</td><td>—</td></tr>
<tr><td>Phú Thọ</td><td>Hòa Bình + Vĩnh Phúc + Phú Thọ</td></tr>
<tr><td rowspan="5"><b>105°00'</b></td><td>TP Hà Nội</td><td>—</td></tr>
<tr><td>Thanh Hóa</td><td>—</td></tr>
<tr><td>Ninh Bình</td><td>Hà Nam + Nam Định + Ninh Bình</td></tr>
<tr><td>Đồng Tháp</td><td>Tiền Giang + Đồng Tháp</td></tr>
<tr><td>TP Cần Thơ</td><td>Sóc Trăng + Hậu Giang + TP Cần Thơ</td></tr>
<tr><td rowspan="3"><b>105°30'</b></td><td>Hà Tĩnh</td><td>—</td></tr>
<tr><td>Hưng Yên</td><td>Hưng Yên + Thái Bình</td></tr>
<tr><td>Vĩnh Long</td><td>Bến Tre + Vĩnh Long + Trà Vinh</td></tr>
<tr><td rowspan="4"><b>105°45'</b></td><td>Cao Bằng</td><td>—</td></tr>
<tr><td>Tây Ninh</td><td>Tây Ninh + Long An</td></tr>
<tr><td>TP Hải Phòng</td><td>TP Hải Phòng + Hải Dương</td></tr>
<tr><td>TP HCM</td><td>Bà Rịa-VT + Bình Dương + TP HCM</td></tr>
<tr><td rowspan="2"><b>106°00'</b></td><td>Quảng Trị</td><td>Quảng Bình + Quảng Trị</td></tr>
<tr><td>Tuyên Quang</td><td>Hà Giang + Tuyên Quang</td></tr>
<tr><td><b>106°30'</b></td><td>Thái Nguyên</td><td>Thái Nguyên + Bắc Kạn</td></tr>
<tr><td rowspan="2"><b>107°00'</b></td><td>Bắc Ninh</td><td>Bắc Ninh + Bắc Giang</td></tr>
<tr><td>TP Huế</td><td>—</td></tr>
<tr><td><b>107°15'</b></td><td>Lạng Sơn</td><td>—</td></tr>
<tr><td rowspan="4"><b>107°45'</b></td><td>Quảng Ninh</td><td>—</td></tr>
<tr><td>Đồng Nai</td><td>Bình Phước + Đồng Nai</td></tr>
<tr><td>Lâm Đồng</td><td>Đắk Nông + Bình Thuận + Lâm Đồng</td></tr>
<tr><td>TP Đà Nẵng</td><td>Quảng Nam + TP Đà Nẵng</td></tr>
<tr><td><b>108°00'</b></td><td>Quảng Ngãi</td><td>Kon Tum + Quảng Ngãi</td></tr>
<tr><td rowspan="2"><b>108°15'</b></td><td>Gia Lai</td><td>Gia Lai + Bình Định</td></tr>
<tr><td>Khánh Hòa</td><td>Ninh Thuận + Khánh Hòa</td></tr>
<tr><td><b>108°30'</b></td><td>Đắk Lắk</td><td>Phú Yên + Đắk Lắk</td></tr>
</table>

<h3>💡 Chọn hệ tọa độ nào?</h3>
<ul>
<li>📍 <b>GPS / bản đồ web:</b> EPSG:4326 (WGS 84)</li>
<li>📐 <b>Tính diện tích / khoảng cách:</b> EPSG:32648 hoặc 32649 (UTM)</li>
<li>🗺️ <b>Bản đồ toàn quốc:</b> EPSG:3405 hoặc 3406 (VN-2000 / 6°)</li>
<li>📏 <b>Địa chính / cấp tỉnh:</b> Tra múi 3° theo tỉnh ở bảng trên</li>
</ul>
<p style="color:#888;font-size:10px"><i>Nguồn: EPSG Registry (epsg.io) — Bộ TN&MT Việt Nam</i></p>"""

    def _crs_legacy_63(self):
        """HTML table of legacy 63 provinces with EPSG Authority IDs."""
        return """
<h2>📋 Danh sách 63 Tỉnh Thành Cũ — Kinh tuyến trục & Authority ID</h2>
<p style="color:#555"><i>Dữ liệu tham khảo (trước sáp nhập). Nguồn: Bộ TN&MT.</i></p>

<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#f5f5f5"><th>STT</th><th>Mã</th><th>Tỉnh/TP</th><th>KTT</th><th>Authority ID</th></tr>
<tr><td>1</td><td>DC01</td><td>An Giang</td><td>104°45'</td><td>EPSG:9208</td></tr>
<tr><td>2</td><td>DC02</td><td>Bà Rịa-Vũng Tàu</td><td>107°45'</td><td>EPSG:5899</td></tr>
<tr><td>3</td><td>DC03</td><td>Bạc Liêu</td><td>105°00'</td><td>EPSG:5896</td></tr>
<tr><td>4</td><td>DC04</td><td>Bắc Giang</td><td>107°00'</td><td>EPSG:9214</td></tr>
<tr><td>5</td><td>DC05</td><td>Bắc Kạn</td><td>106°30'</td><td>EPSG:9213</td></tr>
<tr><td>6</td><td>DC06</td><td>Bắc Ninh</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>7</td><td>DC07</td><td>Bến Tre</td><td>105°45'</td><td>EPSG:9210</td></tr>
<tr><td>8</td><td>DC08</td><td>Bình Dương</td><td>105°45'</td><td>EPSG:9210</td></tr>
<tr><td>9</td><td>DC09</td><td>Bình Định</td><td>108°15'</td><td>EPSG:9217</td></tr>
<tr><td>10</td><td>DC10</td><td>Bình Phước</td><td>106°15'</td><td>EPSG:9212</td></tr>
<tr><td>11</td><td>DC11</td><td>Bình Thuận</td><td>108°30'</td><td>EPSG:9218</td></tr>
<tr><td>12</td><td>DC12</td><td>Cà Mau</td><td>104°30'</td><td>EPSG:9207</td></tr>
<tr><td>13</td><td>DC13</td><td>Cao Bằng</td><td>105°45'</td><td>EPSG:9210</td></tr>
<tr><td>14</td><td>DC14</td><td>Cần Thơ</td><td>105°00'</td><td>EPSG:5896</td></tr>
<tr><td>15</td><td>DC15</td><td>Đà Nẵng</td><td>107°45'</td><td>EPSG:5899</td></tr>
<tr><td>16</td><td>DC16</td><td>Đắk Lắk</td><td>108°30'</td><td>EPSG:9218</td></tr>
<tr><td>17</td><td>DC17</td><td>Đắk Nông</td><td>108°30'</td><td>EPSG:9218</td></tr>
<tr><td>18</td><td>DC18</td><td>Điện Biên</td><td>103°00'</td><td>EPSG:9205</td></tr>
<tr><td>19</td><td>DC19</td><td>Đồng Nai</td><td>107°45'</td><td>EPSG:5899</td></tr>
<tr><td>20</td><td>DC20</td><td>Đồng Tháp</td><td>105°00'</td><td>EPSG:5896</td></tr>
<tr><td>21</td><td>DC21</td><td>Gia Lai</td><td>108°30'</td><td>EPSG:9218</td></tr>
<tr><td>22</td><td>DC22</td><td>Hà Giang</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>23</td><td>DC23</td><td>Hà Nam</td><td>105°00'</td><td>EPSG:5896</td></tr>
<tr><td>24</td><td>DC24</td><td>Hà Nội</td><td>105°00'</td><td>EPSG:5896</td></tr>
<tr><td>25</td><td>DC25</td><td>Hà Tĩnh</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>26</td><td>DC26</td><td>Hải Dương</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>27</td><td>DC27</td><td>Hải Phòng</td><td>105°45'</td><td>EPSG:9210</td></tr>
<tr><td>28</td><td>DC28</td><td>Hậu Giang</td><td>105°00'</td><td>EPSG:5896</td></tr>
<tr><td>29</td><td>DC29</td><td>Hòa Bình</td><td>106°00'</td><td>EPSG:9211</td></tr>
<tr><td>30</td><td>DC30</td><td>TP HCM</td><td>105°45'</td><td>EPSG:9210</td></tr>
<tr><td>31</td><td>DC31</td><td>Hưng Yên</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>32</td><td>DC32</td><td>Khánh Hòa</td><td>108°15'</td><td>EPSG:9217</td></tr>
<tr><td>33</td><td>DC33</td><td>Kiên Giang</td><td>104°30'</td><td>EPSG:9207</td></tr>
<tr><td>34</td><td>DC34</td><td>Kon Tum</td><td>107°30'</td><td>EPSG:9216</td></tr>
<tr><td>35</td><td>DC35</td><td>Lai Châu</td><td>103°00'</td><td>EPSG:9205</td></tr>
<tr><td>36</td><td>DC36</td><td>Lạng Sơn</td><td>107°15'</td><td>EPSG:9215</td></tr>
<tr><td>37</td><td>DC37</td><td>Lào Cai</td><td>104°45'</td><td>EPSG:9208</td></tr>
<tr><td>38</td><td>DC38</td><td>Lâm Đồng</td><td>107°45'</td><td>EPSG:5899</td></tr>
<tr><td>39</td><td>DC39</td><td>Long An</td><td>105°45'</td><td>EPSG:9210</td></tr>
<tr><td>40</td><td>DC40</td><td>Nam Định</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>41</td><td>DC41</td><td>Nghệ An</td><td>104°45'</td><td>EPSG:9208</td></tr>
<tr><td>42</td><td>DC42</td><td>Ninh Bình</td><td>105°00'</td><td>EPSG:5896</td></tr>
<tr><td>43</td><td>DC43</td><td>Ninh Thuận</td><td>108°15'</td><td>EPSG:9217</td></tr>
<tr><td>44</td><td>DC44</td><td>Phú Thọ</td><td>104°45'</td><td>EPSG:9208</td></tr>
<tr><td>45</td><td>DC45</td><td>Phú Yên</td><td>108°30'</td><td>EPSG:9218</td></tr>
<tr><td>46</td><td>DC46</td><td>Quảng Bình</td><td>106°00'</td><td>EPSG:9211</td></tr>
<tr><td>47</td><td>DC47</td><td>Quảng Nam</td><td>107°45'</td><td>EPSG:5899</td></tr>
<tr><td>48</td><td>DC48</td><td>Quảng Ngãi</td><td>108°00'</td><td>EPSG:9216</td></tr>
<tr><td>49</td><td>DC49</td><td>Quảng Ninh</td><td>107°45'</td><td>EPSG:5899</td></tr>
<tr><td>50</td><td>DC50</td><td>Quảng Trị</td><td>106°15'</td><td>EPSG:9212</td></tr>
<tr><td>51</td><td>DC51</td><td>Sóc Trăng</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>52</td><td>DC52</td><td>Sơn La</td><td>104°00'</td><td>EPSG:9206</td></tr>
<tr><td>53</td><td>DC53</td><td>Tây Ninh</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>54</td><td>DC54</td><td>Thái Bình</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>55</td><td>DC55</td><td>Thái Nguyên</td><td>106°30'</td><td>EPSG:9213</td></tr>
<tr><td>56</td><td>DC56</td><td>Thanh Hóa</td><td>105°00'</td><td>EPSG:5896</td></tr>
<tr><td>57</td><td>DC57</td><td>Thừa Thiên Huế</td><td>107°00'</td><td>EPSG:9214</td></tr>
<tr><td>58</td><td>DC58</td><td>Tiền Giang</td><td>105°45'</td><td>EPSG:9210</td></tr>
<tr><td>59</td><td>DC59</td><td>Trà Vinh</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>60</td><td>DC60</td><td>Tuyên Quang</td><td>106°00'</td><td>EPSG:9211</td></tr>
<tr><td>61</td><td>DC61</td><td>Vĩnh Long</td><td>105°30'</td><td>EPSG:9209</td></tr>
<tr><td>62</td><td>DC62</td><td>Vĩnh Phúc</td><td>105°00'</td><td>EPSG:5896</td></tr>
<tr><td>63</td><td>DC63</td><td>Yên Bái</td><td>104°45'</td><td>EPSG:9208</td></tr>
</table>

<p style="color:#888;font-size:10px"><i>⚠️ Dữ liệu tham khảo — Trước sáp nhập hành chính 2026. Nguồn: Bộ TN&MT.</i></p>
"""

    # ── CRS Guide Text ───────────────────────────────────────────

    def _crs_guide_en(self):
        return """
<h2>🌐 CRS Control & Conversion Guide</h2>
<p style="color:#555"><i>Training guide for GPS, QGIS, MapInfo, ArcGIS, Google Earth & Smartphone</i></p>

<h3 style="background:#e3f2fd;padding:6px;border-radius:4px">
📘 Part 1 — Understanding CRS Basics</h3>

<table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#e3f2fd"><th width="30%">System</th><th>Key Info</th></tr>
<tr>
<td>🌍 <b>WGS 84</b><br>EPSG: <b>4326</b></td>
<td>
• <b>Unit:</b> Degrees (or D°M'S")<br>
• <b>Type:</b> Global geographic CRS<br>
• 📱 <b>Required for:</b> Google Earth, Smartphone apps, GPS devices<br>
• ⚠️ Cannot measure area/distance accurately (not projected)
</td>
</tr>
<tr>
<td>🇻🇳 <b>VN-2000</b><br>(Projected, meters)</td>
<td>
• <b>Unit:</b> Meters — ideal for area/distance<br>
• Each province has its own <b>Central Meridian</b> and <b>EPSG code</b><br>
• Example: Thanh Hóa = 5897, Quảng Nam = 5899, Quảng Trị = 9213
</td>
</tr>
</table>

<h4>⚡ Integration vs Internal System (Critical for GPS users!)</h4>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#fff9c4"><th width="35%">Type</th><th>When to use</th></tr>
<tr>
<td>✅ <b>Integration</b><br>(Hệ hội nhập)</td>
<td>Has full 7 parameters (e.g. -192, -39, -111).<br>
→ Map <b>aligns perfectly</b> with satellite basemap on screen.</td>
</tr>
<tr>
<td>⚠️ <b>Internal</b><br>(Hệ nội bộ)</td>
<td>No shift parameters. Use when GPS device is <b>not configured</b> with 7 params.<br>
→ Printed map coords match GPS readout exactly (even if offset from satellite).</td>
</tr>
</table>

<hr>
<h3 style="background:#e8f5e9;padding:6px;border-radius:4px">
🔧 Part 2 — Fixing Misaligned Maps</h3>
<p>When your map is offset from the basemap or "floating in the ocean":</p>

<table border="0" cellpadding="4" style="font-size:11px;width:100%">
<tr><td style="background:#e3f2fd;border-radius:4px;padding:8px">
<b>🔍 Step 1 — Identify the original CRS</b><br>
• Open Basemap (Google Satellite) to compare rivers, roads<br>
• Check coordinates: if values like <code>107.75</code> → <code>0.75 × 60 = 45'</code> → Central meridian = <b>107°45'</b><br>
• Look up the province in the CRS table
</td></tr>
<tr><td style="background:#fff9c4;border-radius:4px;padding:8px">
<b>⚙️ Step 2 — Define / Set CRS (NOT Export!)</b><br>
• ❌ Do <b>NOT</b> use Export/Save As yet!<br>
• ✅ Use <b>"Set Layer CRS"</b> to assign the correct EPSG (e.g. 5899)<br>
• Map will <b>snap to correct position</b> immediately
</td></tr>
<tr><td style="background:#e8f5e9;border-radius:4px;padding:8px">
<b>📤 Step 3 — Reproject (Export)</b><br>
• Only after the map is in the right place<br>
• Export → Save As → choose target CRS (e.g. WGS84 / 4326)
</td></tr>
</table>

<hr>
<h3 style="background:#fce4ec;padding:6px;border-radius:4px">
📱 Part 3 — Export to Smartphone & Google Earth</h3>

<table border="0" cellpadding="4" style="font-size:11px;width:100%">
<tr><td style="background:#f3e5f5;border-radius:4px;padding:8px">
<b>1️⃣ Fix fonts:</b> Convert TCVN3 → Unicode in Attribute Table
</td></tr>
<tr><td style="background:#e8eaf6;border-radius:4px;padding:8px">
<b>2️⃣ Install Plugin:</b> "KML Tools" in QGIS
</td></tr>
<tr><td style="background:#e3f2fd;border-radius:4px;padding:8px">
<b>3️⃣ Export KMZ:</b> Select only essential fields (Owner, Location, Land type, Plot)<br>
❌ Don't export all columns → file too heavy
</td></tr>
<tr><td style="background:#e8f5e9;border-radius:4px;padding:8px">
<b>4️⃣ Share:</b> Send .kmz via Zalo → Open on phone with Google Earth
</td></tr>
</table>

<hr>
<h3 style="background:#fff3e0;padding:6px;border-radius:4px">
🔢 Part 4 — DMS ↔ Decimal Conversion</h3>

<h4>📐 Manual Formula</h4>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:12px;width:100%;background:#fffde7">
<tr><td>
<b>DMS → Decimal:</b>&nbsp;&nbsp; <code style="font-size:14px;background:#fff9c4;padding:4px 8px;border-radius:3px">Decimal = Degrees + Minutes/60 + Seconds/3600</code><br><br>
<b>Example:</b> 105°27'35"<br>
→ 105 + 27/60 + 35/3600 = 105 + 0.45 + 0.00972 = <b style="color:#d32f2f;font-size:13px">105.45972</b>
</td></tr>
<tr><td>
<b>Decimal → DMS:</b><br>
• Degrees = integer part: <b>105</b><br>
• Minutes = (0.45972 × 60) = 27.583 → <b>27'</b><br>
• Seconds = (0.583 × 60) = 34.99 → <b>35"</b><br>
→ Result: <b style="color:#1565c0;font-size:13px">105°27'35"</b>
</td></tr>
</table>

<h4>🖥️ QGIS Formulas (Field Calculator)</h4>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#fff9c4"><th>Direction</th><th>QGIS Formula</th><th>Output Type</th></tr>
<tr>
<td>DMS → Decimal</td>
<td><code>dms_to_degree("column_name")</code></td>
<td>Decimal / Real</td>
</tr>
<tr>
<td>Decimal → DMS</td>
<td><code>to_dms(X)</code> or<br><code>to_dms(transform($geometry, 'EPSG:3405', 'EPSG:4326'))</code></td>
<td>Text / String</td>
</tr>
</table>
<p>💡 Use <b>Field Calculator</b> in Attribute Table to batch-convert entire columns.</p>
"""

    def _crs_guide_vn(self):
        return """
<h2>🌐 Hướng dẫn Kiểm soát & Chuyển đổi Hệ tọa độ</h2>
<p style="color:#555"><i>Tài liệu đào tạo cho GPS, QGIS, MapInfo, ArcGIS, Google Earth & Smartphone</i></p>

<h3 style="background:#e3f2fd;padding:6px;border-radius:4px">
📘 Phần 1 — Hiểu đúng về CRS cơ bản</h3>

<table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#e3f2fd"><th width="30%">Hệ tọa độ</th><th>Thông tin chính</th></tr>
<tr>
<td>🌍 <b>WGS 84</b><br>EPSG: <b>4326</b></td>
<td>
• <b>Đơn vị:</b> Độ (hoặc Độ Phút Giây)<br>
• <b>Loại:</b> Hệ tọa độ địa lý toàn cầu<br>
• 📱 <b>Bắt buộc cho:</b> Google Earth, App điện thoại, máy GPS<br>
• ⚠️ Không đo diện tích/khoảng cách chính xác (chưa chiếu phẳng)
</td>
</tr>
<tr>
<td>🇻🇳 <b>VN-2000</b><br>(Hệ phẳng, mét)</td>
<td>
• <b>Đơn vị:</b> Mét — lý tưởng để đo diện tích/khoảng cách<br>
• Mỗi tỉnh có <b>Kinh tuyến trục</b> và <b>mã EPSG</b> riêng<br>
• Ví dụ: Thanh Hóa = 5897, Quảng Nam = 5899, Quảng Trị = 9213
</td>
</tr>
</table>

<h4>⚡ Hệ Hội nhập vs Hệ Nội bộ (Rất quan trọng khi đo GPS!)</h4>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#fff9c4"><th width="35%">Loại</th><th>Khi nào dùng</th></tr>
<tr>
<td>✅ <b>Hệ hội nhập</b></td>
<td>Có đủ 7 tham số (ví dụ: -192, -39, -111).<br>
→ Bản đồ <b>khớp hoàn hảo</b> với ảnh vệ tinh (Basemap) trên máy tính.</td>
</tr>
<tr>
<td>⚠️ <b>Hệ nội bộ</b></td>
<td>Không có tham số dịch chuyển. Dùng khi GPS cầm tay <b>chưa cài 7 tham số</b>.<br>
→ Tọa độ in ra <b>khớp với số đọc trên GPS</b> (dù lệch ảnh vệ tinh).</td>
</tr>
</table>

<hr>
<h3 style="background:#e8f5e9;padding:6px;border-radius:4px">
🔧 Phần 2 — Xử lý Bản đồ bị lệch</h3>
<p>Khi mở file thấy bản đồ lệch ảnh vệ tinh hoặc nằm giữa biển:</p>

<table border="0" cellpadding="4" style="font-size:11px;width:100%">
<tr><td style="background:#e3f2fd;border-radius:4px;padding:8px">
<b>🔍 Bước 1 — Xác định hệ tọa độ gốc</b><br>
• Mở Basemap (Google Satellite) để đối chiếu sông, đường<br>
• Kiểm tra tọa độ: nếu thấy <code>107.75</code> → <code>0.75 × 60 = 45'</code> → Kinh tuyến trục = <b>107°45'</b><br>
• Tra bảng CRS để biết thuộc tỉnh nào
</td></tr>
<tr><td style="background:#fff9c4;border-radius:4px;padding:8px">
<b>⚙️ Bước 2 — Định nghĩa lại CRS (KHÔNG Export!)</b><br>
• ❌ <b>TUYỆT ĐỐI</b> không dùng Export/Save As vội!<br>
• ✅ Dùng <b>"Set Layer CRS"</b> để ép đúng mã EPSG (ví dụ: 5899)<br>
• Bản đồ sẽ <b>nhảy về đúng vị trí</b> ngay lập tức
</td></tr>
<tr><td style="background:#e8f5e9;border-radius:4px;padding:8px">
<b>📤 Bước 3 — Chuyển đổi (Export)</b><br>
• Chỉ khi bản đồ đã nằm đúng vị trí<br>
• Export → Save As → chọn hệ tọa độ đích (ví dụ: WGS84 / 4326)
</td></tr>
</table>

<hr>
<h3 style="background:#fce4ec;padding:6px;border-radius:4px">
📱 Phần 3 — Xuất bản đồ lên Điện thoại & Google Earth</h3>

<table border="0" cellpadding="4" style="font-size:11px;width:100%">
<tr><td style="background:#f3e5f5;border-radius:4px;padding:8px">
<b>1️⃣ Sửa font:</b> Chuyển TCVN3 → Unicode trong Bảng thuộc tính
</td></tr>
<tr><td style="background:#e8eaf6;border-radius:4px;padding:8px">
<b>2️⃣ Cài Plugin:</b> "KML Tools" trong QGIS
</td></tr>
<tr><td style="background:#e3f2fd;border-radius:4px;padding:8px">
<b>3️⃣ Xuất KMZ:</b> Chỉ chọn các trường cần thiết (Chủ rừng, Địa danh, Loại đất, Lô, Khoảnh)<br>
❌ Không chọn hết tất cả → file quá nặng
</td></tr>
<tr><td style="background:#e8f5e9;border-radius:4px;padding:8px">
<b>4️⃣ Chia sẻ:</b> Gửi .kmz qua Zalo → Mở trên điện thoại bằng Google Earth
</td></tr>
</table>

<hr>
<h3 style="background:#fff3e0;padding:6px;border-radius:4px">
🔢 Phần 4 — Chuyển đổi Độ Phút Giây ↔ Số thập phân</h3>

<h4>📐 Công thức thủ công</h4>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:12px;width:100%;background:#fffde7">
<tr><td>
<b>Độ Phút Giây → Thập phân:</b>&nbsp;&nbsp; <code style="font-size:14px;background:#fff9c4;padding:4px 8px;border-radius:3px">Thập phân = Độ + Phút/60 + Giây/3600</code><br><br>
<b>Ví dụ:</b> 105°27'35"<br>
→ 105 + 27/60 + 35/3600 = 105 + 0.45 + 0.00972 = <b style="color:#d32f2f;font-size:13px">105.45972</b>
</td></tr>
<tr><td>
<b>Thập phân → Độ Phút Giây:</b><br>
• Độ = phần nguyên: <b>105</b><br>
• Phút = (0.45972 × 60) = 27.583 → <b>27'</b><br>
• Giây = (0.583 × 60) = 34.99 → <b>35"</b><br>
→ Kết quả: <b style="color:#1565c0;font-size:13px">105°27'35"</b>
</td></tr>
</table>

<h4>🖥️ Công thức QGIS (Field Calculator)</h4>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:11px;width:100%">
<tr style="background:#fff9c4"><th>Chiều</th><th>Công thức QGIS</th><th>Kiểu cột</th></tr>
<tr>
<td>Độ Phút Giây → Thập phân</td>
<td><code>dms_to_degree("tên_cột")</code></td>
<td>Decimal / Real</td>
</tr>
<tr>
<td>Thập phân → Độ Phút Giây</td>
<td><code>to_dms(X)</code> hoặc<br><code>to_dms(transform($geometry, 'EPSG:3405', 'EPSG:4326'))</code></td>
<td>Text / Chuỗi</td>
</tr>
</table>
<p>💡 Dùng <b>Field Calculator</b> trong Bảng thuộc tính để chuyển đổi hàng loạt.</p>
"""

    # ── Collect Parameters ───────────────────────────────────────

    def _collect_params(self):
        """Gather all UI values into a dict for the engine."""
        mode = MODE_PRINT if self.rad_print.isChecked() else MODE_SLIDE
        lang = "EN" if self.cmb_lang.currentIndex() == 0 else "VN"

        paper_key = self.cmb_paper.currentText()
        is_custom = paper_key == "Custom / Tự chọn"
        drawn_extent = getattr(self, "drawn_extent", None)

        if is_custom:
            pw = self.spn_custom_w.value()
            ph = self.spn_custom_h.value()
        else:
            pw, ph = PAPER_SIZES[paper_key]
            # Only apply orientation swap for standard paper sizes
            if self.rad_portrait.isChecked():
                pw, ph = ph, pw

        return {
            "mode": mode,
            "lang": lang,
            "title": self.txt_title.text().strip(),
            "org_name": self.txt_org.text().strip(),
            "study_area": self.txt_study.text().strip(),
            "references": "",  # fixed in template
            "author": self.txt_author.text().strip(),
            "date": self.txt_date.text().strip(),
            "page_width": pw,
            "page_height": ph,
            "auto_scale": self.chk_auto_scale.isChecked(),
            "scale": self.spn_scale.value(),
            "extent_mode": "drawn" if (is_custom and drawn_extent) else "canvas",
            "drawn_extent": drawn_extent,
            "data_sources": self.txt_sources.toPlainText().strip(),
            "show_legend": self.chk_legend.isChecked(),
            "show_north": self.chk_north.isChecked(),
            "north_arrow_svg": self.cmb_arrow.currentData() or "",
            "show_scalebar": self.chk_scalebar.isChecked(),
        }

    # ── Actions ──────────────────────────────────────────────────

    def _on_create(self):
        """Generate layout and open in QGIS layout designer."""
        params = self._collect_params()

        # Validation
        if params["extent_mode"] == "drawn" and not params["drawn_extent"]:
            QMessageBox.warning(
                self, "LVT",
                "Please draw an extent first using the 'Draw Extent' button."
            )
            return

        # Disable button + show wait cursor (no modal dialog to avoid freeze)
        self.btn_create.setEnabled(False)
        self.btn_create.setText("⏳ Creating... / Đang tạo...")
        from qgis.PyQt.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            layout = self.engine.create_layout(params)
            designer = self.iface.openLayoutDesigner(layout)
            try:
                designer.view().zoomFull()
            except Exception:
                pass
            self.iface.messageBar().pushSuccess(
                "LVT", "✅ Layout created! / Đã tạo khung!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_create.setEnabled(True)
            self.btn_create.setText("Create Layout / Tạo khung")
