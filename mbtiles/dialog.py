# -*- coding: utf-8 -*-
"""LVT4U MBTiles Module — Vector Tile Creator Dialog."""
from qgis.PyQt.QtCore import Qt, QSize, QSizeF, QSettings
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
    _SETTINGS_PREFIX = "LVT4U/label/"

    # Factory defaults (used by Reset and first-run)
    _FACTORY = {
        "stroke_color": "#55ff00", "fill_color": "#ffff00",
        "font_color": "#00ffff", "buf_color": "#ffffff",
        "bg_color": "#ffaa00", "stroke_width": 0.5,
        "fill_opacity": 5, "font": "Arial", "font_size": 10,
        "bold": False, "line_height": 20, "underline_count": 8,
        "spacing_lines": 5, "num_sep": "-", "den_sep": "-",
        "num_suffix": "", "den_suffix": "",
        "zoom_in": 1000, "zoom_out": 7500,
        "buffer_on": True, "buffer_size": 2.0,
        "bg_on": False, "bg_radius": 2.0,
    }

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.lang = 'vi'
        self._stroke_color = QColor("#55ff00")
        self._fill_color = QColor("#ffff00")
        self._font_color = QColor("#00ffff")
        self._buf_color = QColor("#ffffff")
        self._bg_color = QColor("#ffaa00")
        self._num_checks = {}
        self._den_checks = {}
        self._num_order = []   # tracks selection sequence
        self._den_order = []
        self.setMinimumSize(820, 600)
        self.resize(860, 650)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()
        self._load_from_qsettings()   # restore last-used values
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
        self.spn_fill_op.setValue(5)
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
        self.spn_line_h.setValue(20)
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

        # Scale visibility — intuitive labels
        self.lbl_zoom_in = QLabel()
        self.cbo_zoom_in = QComboBox()
        for s in _SCALES:
            self.cbo_zoom_in.addItem(f"1:{s:,}".replace(",", "."), s)
        self.cbo_zoom_in.setCurrentIndex(_SCALES.index(1000))
        fg.addWidget(self.lbl_zoom_in, 3, 0)
        fg.addWidget(self.cbo_zoom_in, 3, 1)

        self.lbl_zoom_out = QLabel()
        self.cbo_zoom_out = QComboBox()
        for s in _SCALES:
            self.cbo_zoom_out.addItem(f"1:{s:,}".replace(",", "."), s)
        self.cbo_zoom_out.setCurrentIndex(_SCALES.index(7500))
        fg.addWidget(self.lbl_zoom_out, 3, 2)
        fg.addWidget(self.cbo_zoom_out, 3, 3)

        # Buffer (label outline)
        self.chk_buffer = QCheckBox()
        self.chk_buffer.setChecked(True)
        fg.addWidget(self.chk_buffer, 4, 0)

        self.lbl_buf_color = QLabel()
        self.btn_buf_color = QPushButton()
        self.btn_buf_color.setFixedSize(70, 22)
        self.btn_buf_color.clicked.connect(lambda: self._pick_color("buffer"))
        fg.addWidget(self.lbl_buf_color, 4, 1)
        fg.addWidget(self.btn_buf_color, 4, 2)

        self.lbl_buf_size = QLabel()
        self.spn_buf_size = QDoubleSpinBox()
        self.spn_buf_size.setRange(0.1, 10.0)
        self.spn_buf_size.setValue(1.0)
        self.spn_buf_size.setSingleStep(0.5)
        self.spn_buf_size.setSuffix(" mm")
        fg.addWidget(self.lbl_buf_size, 4, 3)
        fg.addWidget(self.spn_buf_size, 4, 4)

        # Background (label background shape)
        self.chk_bg = QCheckBox()
        self.chk_bg.setChecked(False)
        fg.addWidget(self.chk_bg, 5, 0)

        self.lbl_bg_color = QLabel()
        self.btn_bg_color = QPushButton()
        self.btn_bg_color.setFixedSize(70, 22)
        self.btn_bg_color.clicked.connect(lambda: self._pick_color("bg"))
        fg.addWidget(self.lbl_bg_color, 5, 1)
        fg.addWidget(self.btn_bg_color, 5, 2)

        self.lbl_bg_radius = QLabel()
        self.spn_bg_radius = QDoubleSpinBox()
        self.spn_bg_radius.setRange(0, 20.0)
        self.spn_bg_radius.setValue(2.0)
        self.spn_bg_radius.setSingleStep(0.5)
        self.spn_bg_radius.setSuffix(" mm")
        fg.addWidget(self.lbl_bg_radius, 5, 3)
        fg.addWidget(self.spn_bg_radius, 5, 4)

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

        # ═══ Reset / Save Config ═══
        cfg_row = QHBoxLayout()
        self.btn_reset = QPushButton()
        self.btn_reset.clicked.connect(self._reset_defaults)
        self.btn_reset.setStyleSheet(
            "padding:6px;background:#F57C00;color:white;"
            "font-weight:bold;border-radius:4px;"
        )
        cfg_row.addWidget(self.btn_reset)

        self.btn_save_cfg = QPushButton()
        self.btn_save_cfg.clicked.connect(self._save_config)
        self.btn_save_cfg.setStyleSheet(
            "padding:6px;background:#6A1B9A;color:white;"
            "font-weight:bold;border-radius:4px;"
        )
        cfg_row.addWidget(self.btn_save_cfg)

        self.btn_load_cfg = QPushButton()
        self.btn_load_cfg.clicked.connect(self._load_config)
        self.btn_load_cfg.setStyleSheet(
            "padding:6px;background:#00695C;color:white;"
            "font-weight:bold;border-radius:4px;"
        )
        cfg_row.addWidget(self.btn_load_cfg)
        ly.addLayout(cfg_row)

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
        _MAP = {"stroke": "_stroke_color", "fill": "_fill_color",
                "font": "_font_color", "buffer": "_buf_color",
                "bg": "_bg_color"}
        attr = _MAP[target]
        cur = getattr(self, attr)
        c = QColorDialog.getColor(cur, self)
        if c.isValid():
            setattr(self, attr, c)
            self._update_color_buttons()
            self._update_preview()

    def _update_color_buttons(self):
        for btn, c in [(self.btn_stroke_color, self._stroke_color),
                       (self.btn_fill_color, self._fill_color),
                       (self.btn_font_color, self._font_color),
                       (self.btn_buf_color, self._buf_color),
                       (self.btn_bg_color, self._bg_color)]:
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
        self._populate_checks(self.ly_num, self._num_checks, fields, self._num_order)
        self._populate_checks(self.ly_den, self._den_checks, fields, self._den_order)
        self._update_preview()

    def _populate_checks(self, layout, cdict, fields, order_list):
        while layout.count():
            w = layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        cdict.clear()
        order_list.clear()
        for f in fields:
            chk = QCheckBox(f)
            chk.stateChanged.connect(
                lambda state, name=f, ol=order_list: self._on_field_toggled(state, name, ol)
            )
            layout.addWidget(chk)
            cdict[f] = chk

    def _on_field_toggled(self, state, field_name, order_list):
        """Track check order: append on check, remove on uncheck."""
        if state == Qt.Checked:
            if field_name not in order_list:
                order_list.append(field_name)
        else:
            if field_name in order_list:
                order_list.remove(field_name)
        self._update_preview()

    def _checked(self, cdict, order_list):
        """Return checked fields sorted by selection order."""
        return [f for f in order_list if f in cdict and cdict[f].isChecked()]

    # ---- Expression ----
    def _build_expression(self):
        num_f = self._checked(self._num_checks, self._num_order)
        den_f = self._checked(self._den_checks, self._den_order)
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
        num_f = self._checked(self._num_checks, self._num_order)
        den_f = self._checked(self._den_checks, self._den_order)
        nsep = self.edt_num_sep.text() or "-"
        dsep = self.edt_den_sep.text() or "-"
        sz = self.spn_fsize.value()
        lh = self.spn_line_h.value() / 100.0
        is_bold = self.chk_bold.isChecked()

        num_t = nsep.join(num_f) if num_f else "TXB-445"
        den_t = dsep.join(den_f) if den_f else ""
        nsfx = self.edt_num_sfx.text()
        dsfx = self.edt_den_sfx.text()
        if nsfx and num_f:
            num_t += " " + nsfx
        if not num_f and not den_f:
            den_t = "12.5 ha"
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

        # ---- Build label lines exactly like QGIS expression ----
        font = QFont(self.cbo_font.currentFont())
        font.setPointSize(sz)
        font.setBold(is_bold)
        p.setFont(font)

        fm = p.fontMetrics()
        base_h = fm.height()
        line_gap = int(base_h * lh)  # line height percentage

        if den_t:
            uline = "_" * self.spn_uline.value()
            n_spacing = self.spn_spacing.value()
            # Build lines: numerator, underline, N empty lines, denominator
            lines = [num_t, uline] + [""] * n_spacing + [den_t]
        else:
            lines = [num_t]

        # Calculate total block height (every line gets line_gap, including empty)
        total_h = line_gap * len(lines)
        start_y = (ph - total_h) // 2 + fm.ascent()

        # Measure max text width for background
        max_tw = 0
        for line in lines:
            if line:
                tw = fm.horizontalAdvance(line)
                if tw > max_tw:
                    max_tw = tw

        cx = pw // 2  # center x

        # ---- Draw label background (if enabled) ----
        if self.chk_bg.isChecked():
            bg_pad = 4
            bg_x = cx - max_tw // 2 - bg_pad
            bg_y = start_y - fm.ascent() - bg_pad
            bg_w = max_tw + bg_pad * 2
            bg_h = total_h + bg_pad * 2
            r = self.spn_bg_radius.value() * 2  # scale up for preview
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(self._bg_color))
            p.drawRoundedRect(bg_x, bg_y, bg_w, bg_h, r, r)

        # ---- Draw each line with buffer + text ----
        for i, line in enumerate(lines):
            if not line:  # empty spacing line → just skip (gap is in line_gap)
                continue
            tw = fm.horizontalAdvance(line)
            tx = cx - tw // 2
            ty = start_y + i * line_gap

            # Buffer (text outline) — draw text in buffer color slightly offset in 8 dirs
            if self.chk_buffer.isChecked():
                buf_size = max(1, int(self.spn_buf_size.value()))
                p.setPen(QPen(self._buf_color))
                p.setFont(font)
                for dx in range(-buf_size, buf_size + 1):
                    for dy in range(-buf_size, buf_size + 1):
                        if dx == 0 and dy == 0:
                            continue
                        p.drawText(tx + dx, ty + dy, line)

            # Main text
            p.setPen(QPen(self._font_color))
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
            self.lbl_zoom_in.setText("🔍+ Gần:")
            self.lbl_zoom_out.setText("🔍− Xa:")
        else:
            self.lbl_zoom_in.setText("🔍+ Near:")
            self.lbl_zoom_out.setText("🔍− Far:")
        self.lbl_preview_l.setText(self._t("Preview:"))
        if self.lang == 'vi':
            self.chk_buffer.setText("Viền chữ")
            self.lbl_buf_color.setText("Màu:")
            self.lbl_buf_size.setText("Dày:")
            self.chk_bg.setText("Nền chữ")
            self.lbl_bg_color.setText("Màu:")
            self.lbl_bg_radius.setText("Bo góc:")
        else:
            self.chk_buffer.setText("Buffer")
            self.lbl_buf_color.setText("Color:")
            self.lbl_buf_size.setText("Size:")
            self.chk_bg.setText("Background")
            self.lbl_bg_color.setText("Color:")
            self.lbl_bg_radius.setText("Radius:")
        self.chk_sat_bg.setText(
            "🛰️ Nền vệ tinh" if self.lang == 'vi' else "🛰️ Satellite BG"
        )
        self.btn_apply.setText("🎨 " + self._t("Apply Style"))
        self.btn_export.setText("📦 Export MBTiles")
        self.btn_draw.setText("📌 " + self._t("Draw Extent"))
        self.btn_layer_ext.setText("🗺️ " + self._t("Use Layer Extent"))
        self.lbl_minz.setText(self._t("Min Zoom:"))
        self.lbl_maxz.setText(self._t("Max Zoom:"))
        if self.lang == 'vi':
            self.btn_reset.setText("🔄 Đặt lại")
            self.btn_save_cfg.setText("💾 Lưu cấu hình")
            self.btn_load_cfg.setText("📂 Tải cấu hình")
            self.txt_guide.setHtml("""
            <h2 style='color:#1B5E20;'>Hướng dẫn sử dụng MBTiles Creator</h2>
            <h3>Bước 1 — Chọn lớp dữ liệu</h3>
            <p>Chọn lớp vector polygon từ danh sách. Thông tin hình học và số đối tượng sẽ hiển thị tự động.</p>

            <h3>Bước 2 — Thiết lập nét lực / nền polygon</h3>
            <p><b>Nét lực (Stroke):</b> Chọn màu viền lô (#55ff00 = xanh lá) và độ rộng (mặc định 0.5 px).<br>
            <b>Nền (Fill):</b> Chọn màu nền lô (#ffff00 = vàng) và độ mờ (mặc định 5% = gần trong suốt).</p>

            <h3>Bước 3 — Cấu hình Nhãn lô (dạng phân số)</h3>
            <p>☑ Tick <b>"Hiển thị nhãn"</b> để bật.</p>
            <p><b>▲ Tử số (trên):</b> Tick các trường muốn hiển thị. Thứ tự tick = thứ tự hiển thị từ trái → phải.<br>
            <b>▼ Mẫu số (dưới):</b> Tick các trường tương tự.<br>
            <b>Nối:</b> Ký tự nối giữa các trường (mặc định "-").<br>
            <b>Hậu tố:</b> Thêm đơn vị sau giá trị (ví dụ: "ha", "cây", "m²").</p>

            <h3>Bước 4 — Phông chữ & Định dạng</h3>
            <p><b>Phông:</b> Chọn font (mặc định Arial).<br>
            <b>Cỡ:</b> Kích thước chữ (pt).<br>
            <b>Màu:</b> Màu chữ (#00ffff = cyan).<br>
            <b>Đậm:</b> Tick nếu muốn in đậm.<br>
            <b>Giãn dòng (%):</b> Khoảng cách giữa tử số và mẫu số. <i>20% = compact</i>, 100% = bình thường.<br>
            <b>Số gạch dưới:</b> Số ký tự "_" ngăn cách tử/mẫu.<br>
            <b>Số dòng giãn:</b> Số dòng trống thêm giữa gạch và mẫu số.</p>

            <h3>Bước 5 — Tỷ lệ hiển thị</h3>
            <p><b>🔍+ Gần:</b> Tỷ lệ khi zoom gần nhất (mặc định 1:1.000).<br>
            <b>🔍− Xa:</b> Tỷ lệ khi zoom xa nhất (mặc định 1:7.500).<br>
            Nhãn chỉ hiển thị khi bản đồ nằm trong khoảng này.</p>

            <h3>Bước 6 — Viền chữ & Nền chữ</h3>
            <p><b>☑ Viền chữ (Buffer):</b> Tạo viền xung quanh chữ giúp dễ đọc. Chọn màu và độ dày (mm).<br>
            <b>☐ Nền chữ (Background):</b> Khung nền phía sau nhãn. Chọn màu, bo góc (mm).</p>

            <h3>Bước 7 — Xem trước</h3>
            <p>Khu vực <b>"Xem trước"</b> hiển thị nhãn trên nền polygon ngay khi thay đổi.<br>
            ☑ <b>Nền vệ tinh:</b> Bật tắt ảnh nền để kiểm tra tương phản.</p>

            <h3>Bước 8 — Áp dụng / Xuất</h3>
            <p>🎨 <b>Áp dụng kiểu:</b> Gán tất cả cài đặt lên layer QGIS ngay lập tức.<br>
            📦 <b>Export MBTiles:</b> Xuất vùng chọn thành file .mbtiles.<br>
            🔄 <b>Đặt lại:</b> Khôi phục toàn bộ về mặc định.<br>
            💾 <b>Lưu cấu hình:</b> Lưu cài đặt hiện tại ra file JSON.<br>
            📂 <b>Tải cấu hình:</b> Nạp lại cài đặt từ file JSON đã lưu.</p>
            """)
        else:
            self.btn_reset.setText("🔄 Reset")
            self.btn_save_cfg.setText("💾 Save Config")
            self.btn_load_cfg.setText("📂 Load Config")
            self.txt_guide.setHtml("""
            <h2 style='color:#1B5E20;'>MBTiles Creator — Step-by-Step Guide</h2>
            <h3>Step 1 — Select Layer</h3>
            <p>Choose a vector polygon layer from the dropdown. Geometry type and feature count are shown automatically.</p>

            <h3>Step 2 — Stroke & Fill</h3>
            <p><b>Stroke:</b> Pick outline color (#55ff00 = green) and width (default 0.5 px).<br>
            <b>Fill:</b> Pick fill color (#ffff00 = yellow) and opacity (default 5% = nearly transparent).</p>

            <h3>Step 3 — Configure Plot Label (Fraction format)</h3>
            <p>☑ Check <b>"Show Label"</b> to enable.</p>
            <p><b>▲ Numerator (top):</b> Check fields to display. Check order = display order left → right.<br>
            <b>▼ Denominator (bottom):</b> Check fields similarly.<br>
            <b>Sep:</b> Separator character between fields (default "-").<br>
            <b>Suffix:</b> Append unit after value (e.g. "ha", "trees", "m²").</p>

            <h3>Step 4 — Font & Formatting</h3>
            <p><b>Font:</b> Select font (default Arial).<br>
            <b>Size:</b> Point size.<br>
            <b>Color:</b> Font color (#00ffff = cyan).<br>
            <b>Bold:</b> Check to bold.<br>
            <b>Line Height (%):</b> Spacing between numerator and denominator. <i>20% = compact</i>, 100% = normal.<br>
            <b>Underline count:</b> Number of "_" chars.<br>
            <b>Spacing lines:</b> Extra blank lines between underline and denominator.</p>

            <h3>Step 5 — Scale Visibility</h3>
            <p><b>🔍+ Near:</b> Most zoomed-in scale (default 1:1,000).<br>
            <b>🔍− Far:</b> Most zoomed-out scale (default 1:7,500).<br>
            Labels only render when the map is within this range.</p>

            <h3>Step 6 — Buffer & Background</h3>
            <p><b>☑ Buffer:</b> Text outline for readability. Pick color and size (mm).<br>
            <b>☐ Background:</b> Rectangle behind label. Pick color and corner radius (mm).</p>

            <h3>Step 7 — Preview</h3>
            <p>The <b>"Preview"</b> area renders the label on the polygon live.<br>
            ☑ <b>Satellite BG:</b> Toggle satellite background to check contrast.</p>

            <h3>Step 8 — Apply / Export</h3>
            <p>🎨 <b>Apply Style:</b> Apply all settings to the QGIS layer instantly.<br>
            📦 <b>Export MBTiles:</b> Export selected area as .mbtiles file.<br>
            🔄 <b>Reset:</b> Restore all settings to defaults.<br>
            💾 <b>Save Config:</b> Save current settings to a JSON file.<br>
            📂 <b>Load Config:</b> Load settings from a previously saved JSON file.</p>
            """)

        self._update_color_buttons()
        self._update_preview()

    # ---- Reset / Save / Load Config ----
    def _reset_defaults(self):
        """Restore all controls to factory defaults and clear saved settings."""
        d = self._FACTORY
        self._stroke_color = QColor(d["stroke_color"])
        self._fill_color = QColor(d["fill_color"])
        self._font_color = QColor(d["font_color"])
        self._buf_color = QColor(d["buf_color"])
        self._bg_color = QColor(d["bg_color"])
        self.spn_stroke_w.setValue(d["stroke_width"])
        self.spn_fill_op.setValue(d["fill_opacity"])
        self.cbo_font.setCurrentFont(QFont(d["font"]))
        self.spn_fsize.setValue(d["font_size"])
        self.chk_bold.setChecked(d["bold"])
        self.spn_line_h.setValue(d["line_height"])
        self.spn_uline.setValue(d["underline_count"])
        self.spn_spacing.setValue(d["spacing_lines"])
        self.edt_num_sep.setText(d["num_sep"])
        self.edt_den_sep.setText(d["den_sep"])
        self.edt_num_sfx.setText(d["num_suffix"])
        self.edt_den_sfx.setText(d["den_suffix"])
        self.cbo_zoom_in.setCurrentIndex(_SCALES.index(d["zoom_in"]))
        self.cbo_zoom_out.setCurrentIndex(_SCALES.index(d["zoom_out"]))
        self.chk_buffer.setChecked(d["buffer_on"])
        self.spn_buf_size.setValue(d["buffer_size"])
        self.chk_bg.setChecked(d["bg_on"])
        self.spn_bg_radius.setValue(d["bg_radius"])
        # Clear saved QSettings
        s = QSettings()
        s.remove(self._SETTINGS_PREFIX)
        self._update_color_buttons()
        self._update_preview()
        QMessageBox.information(self, "LVT4U",
            "Đã khôi phục mặc định." if self.lang == 'vi' else "Defaults restored.")

    def _save_config(self):
        """Save current settings to a JSON file."""
        import json
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Config", "", "JSON (*.json)")
        if not path:
            return
        cfg = self._current_config()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "LVT4U",
            f"Đã lưu: {path}" if self.lang == 'vi' else f"Saved: {path}")

    def _load_config(self):
        """Load settings from a JSON file."""
        import json
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Config", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "LVT4U", str(e))
            return
        self._stroke_color = QColor(cfg.get("stroke_color", "#55ff00"))
        self._fill_color = QColor(cfg.get("fill_color", "#ffff00"))
        self._font_color = QColor(cfg.get("font_color", "#00ffff"))
        self._buf_color = QColor(cfg.get("buf_color", "#ffffff"))
        self._bg_color = QColor(cfg.get("bg_color", "#ffaa00"))
        self.spn_stroke_w.setValue(cfg.get("stroke_width", 0.5))
        self.spn_fill_op.setValue(cfg.get("fill_opacity", 5))
        self.cbo_font.setCurrentFont(QFont(cfg.get("font", "Arial")))
        self.spn_fsize.setValue(cfg.get("font_size", 10))
        self.chk_bold.setChecked(cfg.get("bold", False))
        self.spn_line_h.setValue(cfg.get("line_height", 20))
        self.spn_uline.setValue(cfg.get("underline_count", 8))
        self.spn_spacing.setValue(cfg.get("spacing_lines", 5))
        self.edt_num_sep.setText(cfg.get("num_sep", "-"))
        self.edt_den_sep.setText(cfg.get("den_sep", "-"))
        self.edt_num_sfx.setText(cfg.get("num_suffix", ""))
        self.edt_den_sfx.setText(cfg.get("den_suffix", ""))
        zi = cfg.get("zoom_in", 1000)
        zo = cfg.get("zoom_out", 7500)
        if zi in _SCALES:
            self.cbo_zoom_in.setCurrentIndex(_SCALES.index(zi))
        if zo in _SCALES:
            self.cbo_zoom_out.setCurrentIndex(_SCALES.index(zo))
        self.chk_buffer.setChecked(cfg.get("buffer_on", True))
        self.spn_buf_size.setValue(cfg.get("buffer_size", 2.0))
        self.chk_bg.setChecked(cfg.get("bg_on", False))
        self.spn_bg_radius.setValue(cfg.get("bg_radius", 2.0))
        self._update_color_buttons()
        self._update_preview()
        QMessageBox.information(self, "LVT4U",
            f"Đã tải: {path}" if self.lang == 'vi' else f"Loaded: {path}")

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
                # maximumScale = most zoomed IN (small denominator)
                # minimumScale = most zoomed OUT (large denominator)
                s.maximumScale = self.cbo_zoom_in.currentData()
                s.minimumScale = self.cbo_zoom_out.currentData()

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
                buf.setEnabled(self.chk_buffer.isChecked())
                buf.setSize(self.spn_buf_size.value())
                buf.setColor(self._buf_color)
                fmt.setBuffer(buf)

                # Label Background
                if self.chk_bg.isChecked():
                    from qgis.core import QgsTextBackgroundSettings
                    bg = QgsTextBackgroundSettings()
                    bg.setEnabled(True)
                    bg.setType(QgsTextBackgroundSettings.ShapeRectangle)
                    bg.setSizeType(QgsTextBackgroundSettings.SizeBuffer)
                    bg.setSize(QSizeF(1, 0.5))
                    bg.setFillColor(self._bg_color)
                    r = self.spn_bg_radius.value()
                    bg.setRadii(QSizeF(r, r))
                    fmt.setBackground(bg)

                s.setFormat(fmt)
                layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
                layer.setLabelsEnabled(True)

        self.progress.setValue(80)
        QApplication.processEvents()

        layer.triggerRepaint()
        self.iface.mapCanvas().refresh()

        self.progress.setValue(100)
        QApplication.processEvents()

        # Persist current settings for next session
        self._save_to_qsettings()

        QMessageBox.information(
            self, "LVT4U",
            "Đã áp dụng kiểu dáng và nhãn!" if self.lang == 'vi'
            else "Style and labels applied!"
        )
        self.progress.setVisible(False)

    # ---- QSettings Persistence ----
    def _current_config(self):
        """Collect current UI state into a dict."""
        return {
            "stroke_color": self._stroke_color.name(),
            "fill_color": self._fill_color.name(),
            "font_color": self._font_color.name(),
            "buf_color": self._buf_color.name(),
            "bg_color": self._bg_color.name(),
            "stroke_width": self.spn_stroke_w.value(),
            "fill_opacity": self.spn_fill_op.value(),
            "font": self.cbo_font.currentFont().family(),
            "font_size": self.spn_fsize.value(),
            "bold": self.chk_bold.isChecked(),
            "line_height": self.spn_line_h.value(),
            "underline_count": self.spn_uline.value(),
            "spacing_lines": self.spn_spacing.value(),
            "num_sep": self.edt_num_sep.text(),
            "den_sep": self.edt_den_sep.text(),
            "num_suffix": self.edt_num_sfx.text(),
            "den_suffix": self.edt_den_sfx.text(),
            "zoom_in": self.cbo_zoom_in.currentData(),
            "zoom_out": self.cbo_zoom_out.currentData(),
            "buffer_on": self.chk_buffer.isChecked(),
            "buffer_size": self.spn_buf_size.value(),
            "bg_on": self.chk_bg.isChecked(),
            "bg_radius": self.spn_bg_radius.value(),
        }

    def _save_to_qsettings(self):
        """Persist current label settings to QSettings."""
        s = QSettings()
        for k, v in self._current_config().items():
            s.setValue(self._SETTINGS_PREFIX + k, v)

    def _load_from_qsettings(self):
        """Load label settings from QSettings (fallback to factory defaults)."""
        s = QSettings()
        d = self._FACTORY
        def g(key):
            v = s.value(self._SETTINGS_PREFIX + key, d[key])
            return v
        self._stroke_color = QColor(str(g("stroke_color")))
        self._fill_color = QColor(str(g("fill_color")))
        self._font_color = QColor(str(g("font_color")))
        self._buf_color = QColor(str(g("buf_color")))
        self._bg_color = QColor(str(g("bg_color")))
        self.spn_stroke_w.setValue(float(g("stroke_width")))
        self.spn_fill_op.setValue(int(g("fill_opacity")))
        self.cbo_font.setCurrentFont(QFont(str(g("font"))))
        self.spn_fsize.setValue(int(g("font_size")))
        self.chk_bold.setChecked(str(g("bold")).lower() in ('true', '1'))
        self.spn_line_h.setValue(int(g("line_height")))
        self.spn_uline.setValue(int(g("underline_count")))
        self.spn_spacing.setValue(int(g("spacing_lines")))
        self.edt_num_sep.setText(str(g("num_sep")))
        self.edt_den_sep.setText(str(g("den_sep")))
        self.edt_num_sfx.setText(str(g("num_suffix")))
        self.edt_den_sfx.setText(str(g("den_suffix")))
        zi = int(g("zoom_in"))
        zo = int(g("zoom_out"))
        if zi in _SCALES:
            self.cbo_zoom_in.setCurrentIndex(_SCALES.index(zi))
        if zo in _SCALES:
            self.cbo_zoom_out.setCurrentIndex(_SCALES.index(zo))
        self.chk_buffer.setChecked(str(g("buffer_on")).lower() in ('true', '1'))
        self.spn_buf_size.setValue(float(g("buffer_size")))
        self.chk_bg.setChecked(str(g("bg_on")).lower() in ('true', '1'))
        self.spn_bg_radius.setValue(float(g("bg_radius")))
        self._update_color_buttons()
        self._update_preview()

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
