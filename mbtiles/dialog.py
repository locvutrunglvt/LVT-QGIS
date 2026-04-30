# -*- coding: utf-8 -*-
"""LVT4U MBTiles Module — Vector Tile Creator Dialog."""
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QColor, QFont, QPainter, QPixmap, QPen, QBrush
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QComboBox, QLineEdit, QPushButton, QSpinBox,
    QDoubleSpinBox, QFileDialog, QMessageBox, QGroupBox,
    QFormLayout, QCheckBox, QScrollArea, QFrame, QColorDialog,
    QFontComboBox, QTextEdit, QProgressBar, QApplication,
    QGridLayout, QSizePolicy,
)
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

_VI = {
    "MBTiles Creator": "Tạo MBTiles",
    "Layer:": "Lớp:", "Geom:": "Hình học:", "Count:": "Số ĐT:",
    "Stroke:": "Nét lực:", "Width:": "Rộng:", "Fill:": "Nền:",
    "Opacity:": "Độ mờ:",
    "Plot Label": "Nhãn lô", "Numerator": "Tử số", "Denominator": "Mẫu số",
    "Sep:": "Nối:", "Font:": "Phông:", "Size:": "Cỡ:", "Color:": "Màu:",
    "Bold": "Đậm", "Show Label": "Hiển thị nhãn",
    "Min Scale:": "Tỷ lệ min:", "Max Scale:": "Tỷ lệ max:",
    "Line Height (%):": "Giãn dòng (%):", "Preview:": "Xem trước:",
    "Underline count:": "Số gạch dưới:",
    "Spacing lines:": "Số dòng giãn:",
    "Draw Extent": "Vẽ phạm vi", "Use Layer Extent": "Theo phạm vi lớp",
    "Min Zoom:": "Zoom min:", "Max Zoom:": "Zoom max:",
    "Apply Style": "Áp dụng kiểu", "Close": "Đóng", "Guide": "Hướng dẫn",
    "No vector layer.": "Chưa chọn lớp vector.",
}

# Predefined round scales for user-friendly selection
_SCALES = [
    1000, 2000, 2500, 3000, 5000, 7500,
    10000, 15000, 20000, 25000, 30000, 50000,
]


def _tr(t, lang='vi'):
    return _VI.get(t, t) if lang == 'vi' else t


class MBTilesDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.lang = 'vi'
        self._stroke_color = QColor("#FF0000")
        self._fill_color = QColor("#FFFF00")
        self._font_color = QColor("#000000")
        self._num_checks = {}
        self._den_checks = {}
        self.setMinimumSize(820, 600)
        self.resize(860, 650)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()
        self._refresh_layers()
        self._refresh_ui_text()

    def _t(self, t):
        return _tr(t, self.lang)

    # ---- UI Setup ----
    def _setup_ui(self):
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.btn_lang = QPushButton()
        self.btn_lang.setFixedWidth(110)
        self.btn_lang.clicked.connect(self._toggle_lang)
        top.addWidget(self.btn_lang)
        top.addStretch()
        root.addLayout(top)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # Main tab
        self.tab_main = QWidget()
        self._build_main_tab()
        self.tabs.addTab(self.tab_main, "")

        # Guide tab
        self.tab_guide = QWidget()
        gl = QVBoxLayout(self.tab_guide)
        self.txt_guide = QTextEdit()
        self.txt_guide.setReadOnly(True)
        gl.addWidget(self.txt_guide)
        self.tabs.addTab(self.tab_guide, "")

        # Bottom
        bl = QHBoxLayout()
        bl.addStretch()
        self.btn_close = QPushButton()
        self.btn_close.clicked.connect(self.close)
        bl.addWidget(self.btn_close)
        root.addLayout(bl)

    def _build_main_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        ly = QVBoxLayout(content)
        ly.setSpacing(8)

        # ═══ Row 1: Layer (left) + Style (right) ═══
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        # Left: Layer
        self.grp_layer = QGroupBox()
        fl = QFormLayout()
        fl.setSpacing(4)
        self.cbo_layer = QComboBox()
        self.cbo_layer.currentIndexChanged.connect(self._on_layer_changed)
        self.lbl_layer = QLabel()
        fl.addRow(self.lbl_layer, self.cbo_layer)
        self.lbl_geom_l = QLabel()
        self.lbl_geom = QLabel("—")
        fl.addRow(self.lbl_geom_l, self.lbl_geom)
        self.lbl_count_l = QLabel()
        self.lbl_count = QLabel("—")
        fl.addRow(self.lbl_count_l, self.lbl_count)
        self.grp_layer.setLayout(fl)
        row1.addWidget(self.grp_layer, 1)

        # Right: Style
        self.grp_style = QGroupBox()
        fs = QGridLayout()
        fs.setSpacing(4)

        self.lbl_stroke = QLabel()
        self.btn_stroke_color = QPushButton()
        self.btn_stroke_color.setFixedSize(70, 22)
        self.btn_stroke_color.clicked.connect(lambda: self._pick_color("stroke"))
        fs.addWidget(self.lbl_stroke, 0, 0)
        fs.addWidget(self.btn_stroke_color, 0, 1)

        self.lbl_stroke_w = QLabel()
        self.spn_stroke_w = QDoubleSpinBox()
        self.spn_stroke_w.setRange(0.1, 10.0)
        self.spn_stroke_w.setValue(0.5)
        self.spn_stroke_w.setSuffix(" px")
        fs.addWidget(self.lbl_stroke_w, 0, 2)
        fs.addWidget(self.spn_stroke_w, 0, 3)

        self.lbl_fill = QLabel()
        self.btn_fill_color = QPushButton()
        self.btn_fill_color.setFixedSize(70, 22)
        self.btn_fill_color.clicked.connect(lambda: self._pick_color("fill"))
        fs.addWidget(self.lbl_fill, 1, 0)
        fs.addWidget(self.btn_fill_color, 1, 1)

        self.lbl_fill_op = QLabel()
        self.spn_fill_op = QSpinBox()
        self.spn_fill_op.setRange(0, 100)
        self.spn_fill_op.setValue(30)
        self.spn_fill_op.setSuffix(" %")
        fs.addWidget(self.lbl_fill_op, 1, 2)
        fs.addWidget(self.spn_fill_op, 1, 3)

        self.grp_style.setLayout(fs)
        row1.addWidget(self.grp_style, 1)
        ly.addLayout(row1)

        # ═══ Row 2: Plot Label ═══
        self.grp_label = QGroupBox()
        lbl_ly = QVBoxLayout()
        lbl_ly.setSpacing(6)

        self.chk_show_label = QCheckBox()
        self.chk_show_label.setChecked(True)
        lbl_ly.addWidget(self.chk_show_label)

        # Two columns: Numerator | Denominator
        cols = QHBoxLayout()
        cols.setSpacing(10)

        # -- Left: Numerator --
        left_box = QVBoxLayout()
        self.lbl_num = QLabel()
        self.lbl_num.setStyleSheet("font-weight:bold;")
        left_box.addWidget(self.lbl_num)

        self.scroll_num = QScrollArea()
        self.scroll_num.setWidgetResizable(True)
        self.scroll_num.setFixedHeight(120)
        self.w_num = QWidget()
        self.ly_num = QVBoxLayout(self.w_num)
        self.ly_num.setSpacing(2)
        self.ly_num.setContentsMargins(4, 4, 4, 4)
        self.scroll_num.setWidget(self.w_num)
        left_box.addWidget(self.scroll_num)

        h_ns = QHBoxLayout()
        self.lbl_num_sep = QLabel()
        self.edt_num_sep = QLineEdit("-")
        self.edt_num_sep.setFixedWidth(40)
        self.lbl_num_sfx = QLabel("Suffix:")
        self.edt_num_sfx = QLineEdit()
        self.edt_num_sfx.setFixedWidth(60)
        self.edt_num_sfx.setPlaceholderText("ha, km...")
        h_ns.addWidget(self.lbl_num_sep)
        h_ns.addWidget(self.edt_num_sep)
        h_ns.addWidget(self.lbl_num_sfx)
        h_ns.addWidget(self.edt_num_sfx)
        h_ns.addStretch()
        left_box.addLayout(h_ns)
        cols.addLayout(left_box)

        # -- Right: Denominator --
        right_box = QVBoxLayout()
        self.lbl_den = QLabel()
        self.lbl_den.setStyleSheet("font-weight:bold;")
        right_box.addWidget(self.lbl_den)

        self.scroll_den = QScrollArea()
        self.scroll_den.setWidgetResizable(True)
        self.scroll_den.setFixedHeight(120)
        self.w_den = QWidget()
        self.ly_den = QVBoxLayout(self.w_den)
        self.ly_den.setSpacing(2)
        self.ly_den.setContentsMargins(4, 4, 4, 4)
        self.scroll_den.setWidget(self.w_den)
        right_box.addWidget(self.scroll_den)

        h_ds = QHBoxLayout()
        self.lbl_den_sep = QLabel()
        self.edt_den_sep = QLineEdit("-")
        self.edt_den_sep.setFixedWidth(40)
        self.lbl_den_sfx = QLabel("Suffix:")
        self.edt_den_sfx = QLineEdit()
        self.edt_den_sfx.setFixedWidth(60)
        self.edt_den_sfx.setPlaceholderText("ha, km...")
        h_ds.addWidget(self.lbl_den_sep)
        h_ds.addWidget(self.edt_den_sep)
        h_ds.addWidget(self.lbl_den_sfx)
        h_ds.addWidget(self.edt_den_sfx)
        h_ds.addStretch()
        right_box.addLayout(h_ds)
        cols.addLayout(right_box)

        lbl_ly.addLayout(cols)

        # Font + Scale row (compact grid)
        fg = QGridLayout()
        fg.setSpacing(4)

        self.lbl_font = QLabel()
        self.cbo_font = QFontComboBox()
        self.cbo_font.setCurrentFont(QFont("Arial"))
        fg.addWidget(self.lbl_font, 0, 0)
        fg.addWidget(self.cbo_font, 0, 1, 1, 2)

        self.lbl_fsize = QLabel()
        self.spn_fsize = QSpinBox()
        self.spn_fsize.setRange(6, 72)
        self.spn_fsize.setValue(10)
        fg.addWidget(self.lbl_fsize, 0, 3)
        fg.addWidget(self.spn_fsize, 0, 4)

        self.lbl_fcolor = QLabel()
        self.btn_font_color = QPushButton()
        self.btn_font_color.setFixedSize(70, 22)
        self.btn_font_color.clicked.connect(lambda: self._pick_color("font"))
        fg.addWidget(self.lbl_fcolor, 1, 0)
        fg.addWidget(self.btn_font_color, 1, 1)

        self.chk_bold = QCheckBox()
        fg.addWidget(self.chk_bold, 1, 2)

        self.lbl_line_h = QLabel()
        self.spn_line_h = QDoubleSpinBox()
        self.spn_line_h.setRange(5, 300)
        self.spn_line_h.setValue(100)
        self.spn_line_h.setSuffix(" %")
        fg.addWidget(self.lbl_line_h, 1, 3)
        fg.addWidget(self.spn_line_h, 1, 4)

        self.lbl_uline = QLabel()
        self.spn_uline = QSpinBox()
        self.spn_uline.setRange(3, 50)
        self.spn_uline.setValue(8)
        fg.addWidget(self.lbl_uline, 2, 0)
        fg.addWidget(self.spn_uline, 2, 1)

        self.lbl_spacing = QLabel()
        self.spn_spacing = QSpinBox()
        self.spn_spacing.setRange(0, 15)
        self.spn_spacing.setValue(5)
        fg.addWidget(self.lbl_spacing, 2, 2)
        fg.addWidget(self.spn_spacing, 2, 3)

        # Scale visibility — ComboBox with predefined round scales
        self.lbl_show_from = QLabel()
        self.cbo_scale_from = QComboBox()
        for s in _SCALES:
            self.cbo_scale_from.addItem(f"1:{s:,}".replace(",", "."), s)
        self.cbo_scale_from.setCurrentIndex(_SCALES.index(5000))
        fg.addWidget(self.lbl_show_from, 3, 0)
        fg.addWidget(self.cbo_scale_from, 3, 1)

        self.lbl_show_to = QLabel()
        self.cbo_scale_to = QComboBox()
        for s in _SCALES:
            self.cbo_scale_to.addItem(f"1:{s:,}".replace(",", "."), s)
        self.cbo_scale_to.setCurrentIndex(_SCALES.index(50000))
        fg.addWidget(self.lbl_show_to, 3, 2)
        fg.addWidget(self.cbo_scale_to, 3, 3)

        lbl_ly.addLayout(fg)

        # Unified Preview: polygon + label in one view
        prev_hdr = QHBoxLayout()
        self.lbl_preview_l = QLabel()
        self.lbl_preview_l.setStyleSheet("font-weight:bold;margin-top:4px;")
        prev_hdr.addWidget(self.lbl_preview_l)
        prev_hdr.addStretch()
        self.chk_sat_bg = QCheckBox()
        self.chk_sat_bg.stateChanged.connect(self._update_preview)
        prev_hdr.addWidget(self.chk_sat_bg)
        lbl_ly.addLayout(prev_hdr)

        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setFixedHeight(120)
        self.lbl_preview.setStyleSheet(
            "background:white;border:1px solid #ccc;border-radius:4px;"
        )
        lbl_ly.addWidget(self.lbl_preview)

        # Expression
        self.txt_expr = QLineEdit()
        self.txt_expr.setReadOnly(True)
        self.txt_expr.setStyleSheet(
            "background:#f0f0f0;font-family:monospace;font-size:11px;"
        )
        lbl_ly.addWidget(self.txt_expr)

        self.grp_label.setLayout(lbl_ly)
        ly.addWidget(self.grp_label)

        # ═══ Extent + Zoom ═══
        self.grp_extent = QGroupBox("Extent & Zoom")
        fe = QGridLayout()
        self.btn_draw = QPushButton()
        self.btn_draw.clicked.connect(self._draw_extent)
        self.btn_draw.setStyleSheet("padding:4px;")
        fe.addWidget(self.btn_draw, 0, 0, 1, 2)
        self.btn_layer_ext = QPushButton()
        self.btn_layer_ext.clicked.connect(self._use_layer_extent)
        self.btn_layer_ext.setStyleSheet("padding:4px;")
        fe.addWidget(self.btn_layer_ext, 0, 2, 1, 2)
        self.lbl_minz = QLabel("Min Zoom:")
        self.spn_minz = QSpinBox()
        self.spn_minz.setRange(0, 22); self.spn_minz.setValue(12)
        fe.addWidget(self.lbl_minz, 1, 0); fe.addWidget(self.spn_minz, 1, 1)
        self.lbl_maxz = QLabel("Max Zoom:")
        self.spn_maxz = QSpinBox()
        self.spn_maxz.setRange(0, 22); self.spn_maxz.setValue(18)
        fe.addWidget(self.lbl_maxz, 1, 2); fe.addWidget(self.spn_maxz, 1, 3)
        self.lbl_extent = QLabel("—")
        self.lbl_extent.setStyleSheet("color:#666;font-size:10px;")
        fe.addWidget(self.lbl_extent, 2, 0, 1, 4)
        self.grp_extent.setLayout(fe)
        ly.addWidget(self.grp_extent)

        # ═══ Buttons ═══
        btn_row = QHBoxLayout()
        self.btn_apply = QPushButton()
        self.btn_apply.clicked.connect(self._apply_to_layer)
        self.btn_apply.setStyleSheet(
            "padding:10px;background:#1B5E20;color:white;"
            "font-weight:bold;border-radius:4px;font-size:13px;"
        )
        btn_row.addWidget(self.btn_apply)

        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self._export_mbtiles)
        self.btn_export.setStyleSheet(
            "padding:10px;background:#0D47A1;color:white;"
            "font-weight:bold;border-radius:4px;font-size:13px;"
        )
        btn_row.addWidget(self.btn_export)
        ly.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        ly.addWidget(self.progress)

        ly.addStretch()
        scroll.setWidget(content)
        tl = QVBoxLayout(self.tab_main)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(scroll)

        # Connections
        for sig in [self.edt_num_sep.textChanged, self.edt_den_sep.textChanged,
                     self.edt_num_sfx.textChanged, self.edt_den_sfx.textChanged,
                     self.spn_fsize.valueChanged, self.chk_bold.stateChanged,
                     self.spn_line_h.valueChanged, self.spn_uline.valueChanged,
                     self.spn_spacing.valueChanged, self.spn_fill_op.valueChanged]:
            sig.connect(self._update_preview)
        self.btn_stroke_color.clicked.connect(self._update_preview)
        self.btn_fill_color.clicked.connect(self._update_preview)

    # ---- Color ----
    def _pick_color(self, target):
        cur = {"stroke": self._stroke_color, "fill": self._fill_color,
               "font": self._font_color}[target]
        c = QColorDialog.getColor(cur, self)
        if c.isValid():
            setattr(self, f"_{target}_color", c)
            self._update_color_buttons()
            self._update_preview()

    def _update_color_buttons(self):
        for btn, c in [(self.btn_stroke_color, self._stroke_color),
                       (self.btn_fill_color, self._fill_color),
                       (self.btn_font_color, self._font_color)]:
            btn.setStyleSheet(
                f"background-color:{c.name()};border:1px solid #888;"
                f"border-radius:3px;"
            )
            btn.setText(c.name())

    # ---- Layer ----
    def _refresh_layers(self):
        self.cbo_layer.blockSignals(True)
        self.cbo_layer.clear()
        for l in QgsProject.instance().mapLayers().values():
            if isinstance(l, QgsVectorLayer):
                self.cbo_layer.addItem(l.name(), l.id())
        self.cbo_layer.blockSignals(False)
        if self.cbo_layer.count() > 0:
            self._on_layer_changed()

    def refresh_layers(self):
        self._refresh_layers()

    def _get_layer(self):
        lid = self.cbo_layer.currentData()
        return QgsProject.instance().mapLayer(lid) if lid else None

    def _on_layer_changed(self):
        layer = self._get_layer()
        if not layer:
            return
        self.lbl_geom.setText(QgsWkbTypes.displayString(layer.wkbType()))
        self.lbl_count.setText(str(layer.featureCount()))
        fields = [f.name() for f in layer.fields()]
        self._populate_checks(self.ly_num, self._num_checks, fields)
        self._populate_checks(self.ly_den, self._den_checks, fields)
        self._update_preview()

    def _populate_checks(self, layout, cdict, fields):
        while layout.count():
            w = layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        cdict.clear()
        for f in fields:
            chk = QCheckBox(f)
            chk.stateChanged.connect(self._update_preview)
            layout.addWidget(chk)
            cdict[f] = chk

    def _checked(self, cdict):
        return [k for k, v in cdict.items() if v.isChecked()]

    # ---- Expression ----
    def _build_expression(self):
        num_f = self._checked(self._num_checks)
        den_f = self._checked(self._den_checks)
        nsep = self.edt_num_sep.text() or "-"
        dsep = self.edt_den_sep.text() or "-"

        if not num_f and not den_f:
            return ""

        # coalesce() ensures NULL fields show blank instead of hiding label
        num_parts = [f"coalesce(\"{f}\", '')" for f in num_f]
        num_expr = (f" || '{nsep}' || ".join(num_parts)) if num_parts else "''"
        nsfx = self.edt_num_sfx.text()
        if nsfx:
            num_expr = f"({num_expr}) || ' {nsfx}'"

        if not den_f:
            return num_expr

        den_parts = [f"coalesce(\"{f}\", '')" for f in den_f]
        den_expr = (f" || '{dsep}' || ".join(den_parts)) if den_parts else "''"
        dsfx = self.edt_den_sfx.text()
        if dsfx:
            den_expr = f"({den_expr}) || ' {dsfx}'"

        # Underline: user-controlled count
        ulen = self.spn_uline.value()
        underline = "_" * ulen

        # Spacing newlines after underline (default 5)
        n_sp = self.spn_spacing.value()
        nl = "'" + "\\n" + "'"  # produces the 4-char string '\n' for QGIS
        spacing = (" || ".join([nl] * max(1, n_sp)))

        expr = "(" + num_expr + ") || '\\n' || '" + underline + "' || " + spacing + " || (" + den_expr + ")"
        return expr

    # ---- Preview ----
    def _update_preview(self):
        num_f = self._checked(self._num_checks)
        den_f = self._checked(self._den_checks)
        nsep = self.edt_num_sep.text() or "-"
        dsep = self.edt_den_sep.text() or "-"
        sz = self.spn_fsize.value()
        lh = self.spn_line_h.value() / 100.0
        is_bold = self.chk_bold.isChecked()

        num_t = nsep.join(num_f) if num_f else "Lo-LDLR"
        den_t = dsep.join(den_f) if den_f else ""
        nsfx = self.edt_num_sfx.text()
        dsfx = self.edt_den_sfx.text()
        if nsfx and num_f:
            num_t += " " + nsfx
        if not num_f and not den_f:
            den_t = "Dtich"
        if dsfx and den_f:
            den_t += " " + dsfx

        # ---- Draw unified preview with QPainter ----
        pw = self.lbl_preview.width() or 400
        ph = self.lbl_preview.height() or 120
        pix = QPixmap(max(pw, 200), max(ph, 100))

        # Background: satellite or white
        if self.chk_sat_bg.isChecked():
            pix.fill(QColor("#2C3E2D"))  # dark green satellite-like
        else:
            pix.fill(QColor(255, 255, 255))

        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)

        # Draw polygon centered
        poly_w = int(pw * 0.55)
        poly_h = int(ph * 0.75)
        px = (pw - poly_w) // 2
        py = (ph - poly_h) // 2
        fc = QColor(self._fill_color)
        fc.setAlpha(int(self.spn_fill_op.value() * 2.55))
        p.setBrush(QBrush(fc))
        pen = QPen(self._stroke_color)
        pen.setWidthF(self.spn_stroke_w.value() * 2)
        p.setPen(pen)
        p.drawRect(px, py, poly_w, poly_h)

        # Draw label text on top
        font = QFont(self.cbo_font.currentFont())
        font.setPointSize(sz)
        font.setBold(is_bold)
        p.setFont(font)
        p.setPen(QPen(self._font_color))

        fm = p.fontMetrics()
        line_gap = int(fm.height() * lh)

        if den_t:
            uline = "_" * self.spn_uline.value()
            n_spacing = self.spn_spacing.value()
            # Build lines exactly like QGIS expression:
            # numerator \n underline \n \n \n \n \n denominator
            lines = [num_t, uline] + [""] * n_spacing + [den_t]
        else:
            lines = [num_t]

        total_h = line_gap * len(lines)
        start_y = (ph - total_h) // 2 + fm.ascent()

        for i, line in enumerate(lines):
            if not line:  # empty spacing line
                continue
            tw = fm.horizontalAdvance(line)
            tx = (pw - tw) // 2
            ty = start_y + i * line_gap
            p.drawText(tx, ty, line)

        p.end()
        self.lbl_preview.setPixmap(pix)

        self.txt_expr.setText(self._build_expression())

    # ---- i18n ----
    def _toggle_lang(self):
        self.lang = 'en' if self.lang == 'vi' else 'vi'
        self._refresh_ui_text()

    def _refresh_ui_text(self):
        self.setWindowTitle("LVT4U — " + self._t("MBTiles Creator"))
        self.btn_lang.setText(
            "🌐 English" if self.lang == 'vi' else "🌐 Tiếng Việt"
        )
        self.tabs.setTabText(0, self._t("MBTiles Creator"))
        self.tabs.setTabText(1, self._t("Guide"))
        self.btn_close.setText(self._t("Close"))

        self.grp_layer.setTitle(self._t("Layer:"))
        self.lbl_layer.setText(self._t("Layer:"))
        self.lbl_geom_l.setText(self._t("Geom:"))
        self.lbl_count_l.setText(self._t("Count:"))

        self.grp_style.setTitle(self._t("Stroke:")[:-1] + " / " + self._t("Fill:")[:-1])
        self.lbl_stroke.setText(self._t("Stroke:"))
        self.lbl_stroke_w.setText(self._t("Width:"))
        self.lbl_fill.setText(self._t("Fill:"))
        self.lbl_fill_op.setText(self._t("Opacity:"))

        self.grp_label.setTitle(self._t("Plot Label"))
        self.chk_show_label.setText(self._t("Show Label"))
        self.lbl_num.setText("▲ " + self._t("Numerator"))
        self.lbl_den.setText("▼ " + self._t("Denominator"))
        self.lbl_num_sep.setText(self._t("Sep:"))
        self.lbl_den_sep.setText(self._t("Sep:"))
        sfx = "Hậu tố:" if self.lang == 'vi' else "Suffix:"
        self.lbl_num_sfx.setText(sfx)
        self.lbl_den_sfx.setText(sfx)
        self.lbl_font.setText(self._t("Font:"))
        self.lbl_fsize.setText(self._t("Size:"))
        self.lbl_fcolor.setText(self._t("Color:"))
        self.chk_bold.setText(self._t("Bold"))
        self.lbl_line_h.setText(self._t("Line Height (%):"))
        self.lbl_uline.setText(self._t("Underline count:"))
        self.lbl_spacing.setText(self._t("Spacing lines:"))
        if self.lang == 'vi':
            self.lbl_show_from.setText("Hiện từ:")
            self.lbl_show_to.setText("Đến:")
        else:
            self.lbl_show_from.setText("Show from:")
            self.lbl_show_to.setText("To:")
        self.lbl_preview_l.setText(self._t("Preview:"))
        self.chk_sat_bg.setText(
            "🛰️ Nền vệ tinh" if self.lang == 'vi' else "🛰️ Satellite BG"
        )
        self.btn_apply.setText("🎨 " + self._t("Apply Style"))
        self.btn_export.setText("📦 Export MBTiles")
        self.btn_draw.setText("📌 " + self._t("Draw Extent"))
        self.btn_layer_ext.setText("🗺️ " + self._t("Use Layer Extent"))
        self.lbl_minz.setText(self._t("Min Zoom:"))
        self.lbl_maxz.setText(self._t("Max Zoom:"))

        self._update_color_buttons()
        self._update_preview()

        vi = self.lang == 'vi'
        if vi:
            self.txt_guide.setHtml("""
            <h2 style='color:#1B5E20;'>Hướng dẫn sử dụng MBTiles Creator</h2>
            <h3>1. Chọn lớp & Kiểu dáng</h3>
            <p>Chọn lớp vector (polygon). Cài đặt màu nét lực, độ rộng nét, màu nền và độ mờ.</p>
            <h3>2. Nhãn lô (Phân số)</h3>
            <p><b>Tử số (cột trái):</b> Tick chọn các trường kết hợp. Ví dụ: LO + LDLR → "LO-LDLR"<br>
            <b>Mẫu số (cột phải):</b> Tick chọn các trường kết hợp. Ví dụ: DTICH<br>
            <b>Ký tự nối:</b> Ký tự giữa các trường (mặc định "-")<br>
            <b>Số gạch dưới:</b> Điều chỉnh số ký tự "_" ngăn cách tử/mẫu số<br>
            <b>Giãn dòng (%):</b> Khoảng cách giữa tử số và mẫu số trên bản đồ (20% = compact, 100% = bình thường)<br>
            <b>Tỷ lệ:</b> Nhãn chỉ hiển trong khoảng tỷ lệ đã cài đặt</p>
            <h3>3. Phạm vi & Zoom</h3>
            <p><b>Vẽ phạm vi:</b> Vẽ hình chữ nhật trên bản đồ để xác định vùng xuất MBTiles<br>
            <b>Theo phạm vi lớp:</b> Sử dụng extent của lớp đang chọn<br>
            <b>Zoom:</b> Mức zoom từ 12 (đô thị) đến 18 (chi tiết nhất)</p>
            <h3>4. Áp dụng</h3>
            <p>Nhấn <b>"Áp dụng kiểu"</b> để set stroke/fill/label lên layer trực tiếp.<br>
            Expression tự động tạo — có thể copy vào QGIS Label nếu cần.</p>
            """)
        else:
            self.txt_guide.setHtml("""
            <h2 style='color:#1B5E20;'>MBTiles Creator Guide</h2>
            <h3>1. Layer & Style</h3>
            <p>Select a vector polygon layer. Configure stroke color/width, fill color/opacity.</p>
            <h3>2. Plot Label (Fraction)</h3>
            <p><b>Numerator (left):</b> Check fields to combine. Example: LO + LDLR → "LO-LDLR"<br>
            <b>Denominator (right):</b> Check fields to combine. Example: DTICH<br>
            <b>Field Sep:</b> Character between fields (default "-")<br>
            <b>Underline count:</b> Number of "_" characters separating numerator/denominator<br>
            <b>Line Height (%):</b> Spacing between numerator and denominator on map (20%=compact, 100%=normal)<br>
            <b>Scale:</b> Labels only visible within the configured scale range</p>
            <h3>3. Extent & Zoom</h3>
            <p><b>Draw Extent:</b> Draw a rectangle on the map to define MBTiles area<br>
            <b>Use Layer Extent:</b> Use the selected layer's bounding box<br>
            <b>Zoom:</b> From 12 (urban) to 18 (maximum detail)</p>
            <h3>4. Apply</h3>
            <p>Click <b>"Apply Style"</b> to set stroke/fill/label on the layer directly.<br>
            Expression is auto-generated — copy to QGIS Label if needed.</p>
            """)

    # ---- Apply ----
    def _apply_to_layer(self):
        layer = self._get_layer()
        if not layer:
            QMessageBox.warning(self, "LVT4U", self._t("No vector layer."))
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.progress.setFormat("Applying... %p%")
        QApplication.processEvents()

        from qgis.core import (
            QgsFillSymbol, QgsSingleSymbolRenderer,
            QgsPalLayerSettings, QgsVectorLayerSimpleLabeling,
            QgsTextFormat, QgsTextBufferSettings, QgsUnitTypes,
        )

        self.progress.setValue(20)
        QApplication.processEvents()

        # Stroke + Fill
        sym = QgsFillSymbol.createSimple({})
        sl = sym.symbolLayer(0)
        sl.setStrokeColor(self._stroke_color)
        sl.setStrokeWidth(self.spn_stroke_w.value())
        fc = QColor(self._fill_color)
        fc.setAlpha(int(self.spn_fill_op.value() * 2.55))
        sl.setFillColor(fc)
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

        self.progress.setValue(50)
        QApplication.processEvents()

        # Labels
        if self.chk_show_label.isChecked():
            expr = self._build_expression()
            if expr:
                s = QgsPalLayerSettings()
                s.fieldName = expr
                s.isExpression = True
                s.scaleVisibility = True
                s.minimumScale = self.cbo_scale_to.currentData()
                s.maximumScale = self.cbo_scale_from.currentData()

                fmt = QgsTextFormat()
                font = self.cbo_font.currentFont()
                font.setPointSize(self.spn_fsize.value())
                font.setBold(self.chk_bold.isChecked())
                fmt.setFont(font)
                fmt.setColor(self._font_color)
                fmt.setSize(self.spn_fsize.value())
                # QGIS RenderPercentage: 1.0 = 100%, 0.2 = 20%
                lh_pct = self.spn_line_h.value() / 100.0
                try:
                    fmt.setLineHeightUnit(QgsUnitTypes.RenderPercentage)
                    fmt.setLineHeight(lh_pct)
                except Exception:
                    # Fallback: try Qgis.RenderUnit enum (QGIS 3.30+)
                    try:
                        from qgis.core import Qgis
                        fmt.setLineHeightUnit(Qgis.RenderUnit.Percentage)
                        fmt.setLineHeight(lh_pct)
                    except Exception:
                        fmt.setLineHeight(lh_pct)

                buf = QgsTextBufferSettings()
                buf.setEnabled(True)
                buf.setSize(1)
                buf.setColor(QColor(255, 255, 255))
                fmt.setBuffer(buf)

                s.setFormat(fmt)
                layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
                layer.setLabelsEnabled(True)

        self.progress.setValue(80)
        QApplication.processEvents()

        layer.triggerRepaint()
        self.iface.mapCanvas().refresh()

        self.progress.setValue(100)
        QApplication.processEvents()

        QMessageBox.information(
            self, "LVT4U",
            "Đã áp dụng kiểu dáng và nhãn!" if self.lang == 'vi'
            else "Style and labels applied!"
        )
        self.progress.setVisible(False)

    # ---- Extent ----
    def _draw_extent(self):
        """Let user draw a rectangle on the map canvas."""
        from qgis.gui import QgsMapToolExtent
        self._extent_tool = QgsMapToolExtent(self.iface.mapCanvas())
        self._extent_tool.extentChanged.connect(self._on_extent_drawn)
        self.iface.mapCanvas().setMapTool(self._extent_tool)
        self.hide()

    def _on_extent_drawn(self, extent):
        self._current_extent = extent
        self.lbl_extent.setText(
            f"Extent: {extent.xMinimum():.2f}, {extent.yMinimum():.2f} "
            f"→ {extent.xMaximum():.2f}, {extent.yMaximum():.2f}"
        )
        self.iface.mapCanvas().unsetMapTool(self._extent_tool)
        self.show()
        self.raise_()

    def _use_layer_extent(self):
        layer = self._get_layer()
        if not layer:
            return
        ext = layer.extent()
        self._current_extent = ext
        self.lbl_extent.setText(
            f"Extent: {ext.xMinimum():.2f}, {ext.yMinimum():.2f} "
            f"→ {ext.xMaximum():.2f}, {ext.yMaximum():.2f}"
        )

    # ---- Export MBTiles ----
    def _export_mbtiles(self):
        layer = self._get_layer()
        if not layer:
            QMessageBox.warning(self, "LVT4U", self._t("No vector layer."))
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export MBTiles", "", "MBTiles (*.mbtiles)"
        )
        if not path:
            return

        import processing
        extent = getattr(self, '_current_extent', layer.extent())
        ext_str = (
            f"{extent.xMinimum()},{extent.xMaximum()},"
            f"{extent.yMinimum()},{extent.yMaximum()}"
            f" [{layer.crs().authid()}]"
        )

        self.progress.setVisible(True)
        self.progress.setValue(10)
        self.progress.setFormat("Exporting MBTiles... %p%")
        QApplication.processEvents()

        try:
            # Try native algorithm first (QGIS 3.32+), fallback to qgis
            alg_name = None
            for name in ['native:tilesxyzmbtiles', 'qgis:tilesxyzmbtiles']:
                try:
                    processing.algorithmHelp(name)
                    alg_name = name
                    break
                except Exception:
                    continue

            if not alg_name:
                raise RuntimeError(
                    "Không tìm thấy thuật toán xuất MBTiles.\n"
                    "Yêu cầu QGIS ≥ 3.32." if self.lang == 'vi'
                    else "MBTiles export algorithm not found.\n"
                    "Requires QGIS ≥ 3.32."
                )

            self.progress.setValue(30)
            QApplication.processEvents()

            processing.run(alg_name, {
                'EXTENT': ext_str,
                'ZOOM_MIN': self.spn_minz.value(),
                'ZOOM_MAX': self.spn_maxz.value(),
                'DPI': 96,
                'BACKGROUND_COLOR': QColor(255, 255, 255, 0),
                'TILE_FORMAT': 0,  # PNG
                'QUALITY': 75,
                'METATILESIZE': 4,
                'OUTPUT_FILE': path,
                'OUTPUT_HTML': '',
            })
            self.progress.setValue(100)
            QApplication.processEvents()
            QMessageBox.information(
                self, "LVT4U",
                f"Xuất MBTiles thành công!\n{path}" if self.lang == 'vi'
                else f"MBTiles exported!\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "LVT4U", str(e))
        finally:
            self.progress.setVisible(False)
