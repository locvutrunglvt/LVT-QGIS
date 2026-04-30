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
    QTabWidget, QWidget, QTextBrowser, QRadioButton,
    QButtonGroup,
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
# ---------------------------------------------------------------------------
# Style definitions — NEW (TT16/2023) and OLD (TCVN 11565:2016)
# ---------------------------------------------------------------------------
_STYLES_NEW = [
    {
        "id": "ldlr_vn",
        "label_vi": "LDLR (mã chữ) — Tiếng Việt",
        "label_en": "LDLR (text code) — Vietnamese",
        "qml": "style_ldlr_vn.qml",
        "classify_attr": "LDLR_VT",
        "value_type": "text",
        "lang": "vi",
        "standard": "new",
    },
    {
        "id": "ldlr_en",
        "label_vi": "LDLR (mã chữ) — Tiếng Anh",
        "label_en": "LDLR (text code) — English",
        "qml": "style_ldlr_en.qml",
        "classify_attr": "LDLR_VT",
        "value_type": "text",
        "lang": "en",
        "standard": "new",
    },
    {
        "id": "code_vn",
        "label_vi": "Code (mã số 1–93) — Tiếng Việt",
        "label_en": "Code (numeric 1–93) — Vietnamese",
        "qml": "style_code_vn.qml",
        "classify_attr": "forest_typ",
        "value_type": "numeric",
        "lang": "vi",
        "standard": "new",
    },
    {
        "id": "code_en",
        "label_vi": "Code (mã số 1–93) — Tiếng Anh",
        "label_en": "Code (numeric 1–93) — English",
        "qml": "style_code_en.qml",
        "classify_attr": "Code",
        "value_type": "numeric",
        "lang": "en",
        "standard": "new",
    },
]

_STYLES_OLD = [
    {
        "id": "old_ldlr_vn",
        "label_vi": "LDLR (mã chữ) — Tiếng Việt",
        "label_en": "LDLR (text code) — Vietnamese",
        "qml": "style_old_ldlr_vn.qml",
        "classify_attr": "LDLR_VT",
        "value_type": "text",
        "lang": "vi",
        "standard": "old",
    },
    {
        "id": "old_ldlr_en",
        "label_vi": "LDLR (mã chữ) — Tiếng Anh",
        "label_en": "LDLR (text code) — English",
        "qml": "style_old_ldlr_en.qml",
        "classify_attr": "LDLR_VT",
        "value_type": "text",
        "lang": "en",
        "standard": "old",
    },
    {
        "id": "old_code_vn",
        "label_vi": "Code (mã số 1–93) — Tiếng Việt",
        "label_en": "Code (numeric 1–93) — Vietnamese",
        "qml": "style_old_code_vn.qml",
        "classify_attr": "forest_typ",
        "value_type": "numeric",
        "lang": "vi",
        "standard": "old",
    },
    {
        "id": "old_code_en",
        "label_vi": "Code (mã số 1–93) — Tiếng Anh",
        "label_en": "Code (numeric 1–93) — English",
        "qml": "style_old_code_en.qml",
        "classify_attr": "Code",
        "value_type": "numeric",
        "lang": "en",
        "standard": "old",
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
        self.setMinimumWidth(640)
        self.setMinimumHeight(520)
        # Open 60% width × 97% height for optimal layout
        try:
            from qgis.PyQt.QtWidgets import QApplication
            screen = QApplication.primaryScreen().availableGeometry()
            w = int(screen.width() * 0.60)
            h = int(screen.height() * 0.97)
            self.resize(w, h)
            # Center on screen
            self.move(
                screen.x() + (screen.width() - w) // 2,
                screen.y() + (screen.height() - h) // 2,
            )
        except Exception:
            self.resize(820, 780)
        self._master = _load_master()
        self._ready = False
        self._build_ui()
        self._ready = True

    # -----------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(4)
        root.setContentsMargins(8, 6, 8, 6)

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

        # --- Tab 3: Appendix 1 TT16/2023 ---
        tab_appendix = QWidget()
        self.tabs.addTab(tab_appendix, "📜 Phụ lục 1 — TT16")
        self._build_appendix_tab(tab_appendix)

        # --- Tab 4: Appendix E TCVN 11565:2016 ---
        tab_appendix_e = QWidget()
        self.tabs.addTab(tab_appendix_e, "📗 Phụ lục E — TCVN 11565")
        self._build_appendix_e_tab(tab_appendix_e)

        # Init
        self._on_layer_changed(self.cmb_layer.currentLayer())
        self._on_style_changed(self.cmb_style.currentIndex())

    def _build_main_tab(self, parent):
        ly = QVBoxLayout(parent)
        ly.setSpacing(8)

        # Standard selector row: Old / New
        std_row = QHBoxLayout()
        std_row.setSpacing(8)
        lbl_std = QLabel("📐 Tiêu chuẩn / Standard:")
        lbl_std.setFont(QFont("Segoe UI", 9, QFont.Bold))
        lbl_std.setStyleSheet("color:#333;")
        std_row.addWidget(lbl_std)

        self._std_group = QButtonGroup(parent)
        self.rb_new = QRadioButton("🆕 TT 16/2023 (mới)")
        self.rb_new.setChecked(True)
        self.rb_new.setStyleSheet(
            "QRadioButton{font-weight:bold;color:#1565c0;padding:4px 12px;"
            "border:2px solid #1565c0;border-radius:4px;background:#e3f2fd;}"
            "QRadioButton:checked{background:#bbdefb;}"
        )
        self.rb_old = QRadioButton("📗 TCVN 11565 (cũ)")
        self.rb_old.setStyleSheet(
            "QRadioButton{font-weight:bold;color:#2e7d32;padding:4px 12px;"
            "border:2px solid #2e7d32;border-radius:4px;background:#e8f5e9;}"
            "QRadioButton:checked{background:#c8e6c9;}"
        )
        self._std_group.addButton(self.rb_new, 0)
        self._std_group.addButton(self.rb_old, 1)
        self._std_group.idClicked.connect(self._on_standard_changed)
        std_row.addWidget(self.rb_new)
        std_row.addWidget(self.rb_old)
        std_row.addStretch()
        ly.addLayout(std_row)

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
        self._populate_styles()  # Fill based on selected standard
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

    # -----------------------------------------------------------------
    # Standard switching helpers
    # -----------------------------------------------------------------
    def _populate_styles(self):
        """Fill style combo based on selected standard (Old/New)."""
        self.cmb_style.blockSignals(True)
        self.cmb_style.clear()
        is_new = self.rb_new.isChecked()
        styles = _STYLES_NEW if is_new else _STYLES_OLD
        prefix = "🆕 " if is_new else "📗 "
        for s in styles:
            label = prefix + _style_label(s)
            self.cmb_style.addItem(label, s)
            # Add tooltip showing QML file
            idx = self.cmb_style.count() - 1
            self.cmb_style.setItemData(
                idx, f"QML: {s['qml']}", Qt.ToolTipRole
            )
        self.cmb_style.blockSignals(False)

    def _on_standard_changed(self, btn_id):
        """Handle Old/New standard toggle."""
        self._populate_styles()
        # Re-trigger style info and field auto-detect
        if self.cmb_style.count() > 0:
            self._on_style_changed(0)

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
    # Appendix 1 — LDLR Classification Summary
    # -----------------------------------------------------------------
    # Group definitions: (prefix_pattern, vi_group, en_group, color)
    _GROUPS = [
        ("TXG,TXB,TXN,TXK,TXP,TXG1,TXB1", "I. Rừng gỗ tự nhiên núi đất — Lá rộng thường xanh",
         "I. Natural timber on soil mountain — Evergreen broadleaved", "#00D000"),
        ("RLG,RLB,RLN,RLK,RLP,RLG1,RLB1", "II. Rừng gỗ tự nhiên núi đất — Lá rộng rụng lá",
         "II. Natural timber on soil mountain — Deciduous", "#C0C000"),
        ("LKG,LKB,LKN,LKK,LKP,LKG1,LKB1", "III. Rừng gỗ tự nhiên núi đất — Lá kim",
         "III. Natural timber on soil mountain — Coniferous", "#FF505A"),
        ("RKG,RKB,RKN,RKK,RKP,RKG1,RKB1", "IV. Rừng gỗ tự nhiên núi đất — Lá rộng lá kim",
         "IV. Natural timber on soil mountain — Mixed broadleaved-coniferous", "#FFA0D0"),
        ("TXDG1,TXDB1,TXDK,TXDB,TXDN,TXDP", "V. Rừng gỗ tự nhiên núi đá",
         "V. Natural timber on rocky mountain", "#00D068"),
        ("RNM1,RNMG,RNMB,RNMN,RNMP,RNP1,RNPG,RNPB,RNPN,RNPP,RNN1,RNN",
         "VI. Rừng gỗ tự nhiên ngập nước",
         "VI. Natural timber on wetland", "#7070FF"),
        ("TLU,NUA,VAU,LOO,TNK,TND", "VII. Rừng tre nứa tự nhiên",
         "VII. Natural bamboo forest", "#D0E0FF"),
        ("HG1,HG2,HGD", "VIII. Rừng hỗn giao gỗ — tre nứa",
         "VIII. Mixed wood-bamboo forest", "#FFD0FF"),
        ("CD,CDD,CDN", "IX. Rừng cau dừa tự nhiên",
         "IX. Natural palm/coconut forest", "#C0C0FF"),
        ("RTG,RTGD,RTM,RTP,RTC,RTTN,RTTND,RTCD,RTCDN,RTCDC,RTK,RTKD,DTR,DTRD,DTRM,DTRP,DTRN,DTRC",
         "X. Rừng trồng & Đất đã trồng",
         "X. Plantation & Newly planted land", "#FFC080"),
        ("DT2,DT2D,DT2M,DT2P,DT1,DT1D,DT1M,DT1P,BC1,BC2,NN,NLD,NLM,NLP,MN,DKH",
         "XI. Đất tái sinh, đất trống, nông nghiệp & khác",
         "XI. Regeneration, open land, agriculture & other", "#00A000"),
    ]

    def _build_appendix_tab(self, parent):
        """Build Appendix 1 summary as an HTML tree view."""
        ly = QVBoxLayout(parent)
        lang = current_language()
        codes = self._master["codes"]
        code_map = {c["text_code"]: c for c in codes}

        html = [
            '<html><body style="font-family:Segoe UI,sans-serif;font-size:12px;">',
            '<h3 style="color:#5d4037;">',
            'Phụ lục 1 — Bảng mã loại đất loại rừng (93 mã)'
            if lang == 'vi' else
            'Appendix 1 — Land & Forest Type Classification (93 codes)',
            '</h3>',
            '<p style="color:#888;font-size:11px;">',
            'Thông tư 16/2023/TT-BNNPTNT — Bộ NN&PTNT'
            if lang == 'vi' else
            'Circular 16/2023/TT-BNNPTNT — MARD Vietnam',
            '</p><hr>',
        ]

        for grp_codes, vi_name, en_name, color in self._GROUPS:
            grp_name = vi_name if lang == 'vi' else en_name
            html.append(
                f'<h4 style="color:{color};margin:8px 0 4px 0;">'
                f'{grp_name}</h4>'
            )
            html.append('<table cellspacing="0" cellpadding="2" '
                        'style="margin-left:12px;border-collapse:collapse;">')
            for tc in grp_codes.split(','):
                tc = tc.strip()
                c = code_map.get(tc)
                if not c:
                    continue
                name = c.get(f"name_{lang}", c.get("name_en", ""))
                hex_c = c["hex"]
                vol = c.get('volume_ha', '—')
                html.append(
                    f'<tr>'
                    f'<td style="width:60px;font-weight:bold;color:#333;">{tc}</td>'
                    f'<td style="width:30px;">'
                    f'<span style="background:{hex_c};padding:1px 8px;'
                    f'border:1px solid #ccc;">&nbsp;</span></td>'
                    f'<td style="color:#555;padding-left:6px;">{name}</td>'
                    f'<td style="color:#0d47a1;padding-left:12px;font-size:11px;">{vol}</td>'
                    f'</tr>'
                )
            html.append('</table>')

        html.append('</body></html>')

        browser = QTextBrowser()
        browser.setHtml('\n'.join(html))
        browser.setOpenExternalLinks(False)
        ly.addWidget(browser)

    # -----------------------------------------------------------------
    # Appendix E — TCVN 11565:2016 Color Classification
    # -----------------------------------------------------------------
    def _build_appendix_e_tab(self, parent):
        """Build Appendix E (TCVN 11565:2016) color table."""
        ly = QVBoxLayout(parent)

        # Load Appendix E data
        ae_path = os.path.join(_DATA_DIR, 'tcvn11565_appendix_e.json')
        try:
            with open(ae_path, 'r', encoding='utf-8') as f:
                ae_data = json.load(f)
        except Exception:
            ly.addWidget(QLabel('Could not load TCVN 11565 Appendix E data.'))
            return

        ae_codes = ae_data.get('codes', [])
        tt16_map = {c['text_code']: c for c in self._master['codes']}

        lang = current_language()
        html = [
            '<html><body style="font-family:Segoe UI,sans-serif;font-size:12px;">',
            '<h3 style="color:#2e7d32;">Phụ lục E — TCVN 11565:2016</h3>',
            '<p style="color:#888;font-size:11px;">',
            'Bảng mã màu hiện trạng rừng theo TCVN 11565:2016 (cũ) — '
            'So sánh với TT 16/2023 (mới)',
            '</p><hr>',
            '<table cellspacing="0" cellpadding="3" '
            'style="border-collapse:collapse;width:100%;">',
            '<tr style="background:#e8f5e9;font-weight:bold;">',
            '<td style="width:30px;">STT</td>',
            '<td style="width:60px;">Mã</td>',
            '<td style="width:70px;">TCVN 11565</td>',
            '<td style="width:70px;">TT16/2023</td>',
            '<td>Khớp?</td>',
            '</tr>',
        ]

        diffs = 0
        for ae in ae_codes:
            code = ae['code']
            ae_hex = ae['hex'].upper()
            tt16_entry = tt16_map.get(code)
            tt16_hex = tt16_entry['hex'].upper() if tt16_entry else '—'

            match = '✅' if tt16_hex == ae_hex else '⚠️'
            if tt16_hex != ae_hex and tt16_hex != '—':
                diffs += 1
                row_bg = '#fff3e0'
            else:
                row_bg = '#fff'

            html.append(
                f'<tr style="background:{row_bg};">'
                f'<td>{ae["num"]}</td>'
                f'<td style="font-weight:bold;">{code}</td>'
                f'<td><span style="background:{ae_hex};padding:1px 10px;'
                f'border:1px solid #ccc;">&nbsp;</span> {ae_hex}</td>'
                f'<td><span style="background:{tt16_hex};padding:1px 10px;'
                f'border:1px solid #ccc;">&nbsp;</span> {tt16_hex}</td>'
                f'<td>{match}</td>'
                f'</tr>'
            )

        html.append('</table>')
        html.append(
            f'<p style="margin-top:8px;color:#555;">'
            f'Tổng: {len(ae_codes)} mã | Khác biệt: {diffs} mã</p>'
        )
        html.append('</body></html>')

        browser = QTextBrowser()
        browser.setHtml('\n'.join(html))
        browser.setOpenExternalLinks(False)
        ly.addWidget(browser)

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
        qml_name = style["qml"]
        std = style.get("standard", "new")
        std_label = "🆕 TT16" if std == "new" else "📗 TCVN"
        self.lbl_style_info.setText(
            f'QML field: "{attr}" ({vtype})  |  {std_label}  →  {qml_name}'
        )

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

        std_tag = "TT16/2023" if style.get("standard") == "new" else "TCVN-11565"
        self.iface.messageBar().pushSuccess(
            "LVT4U",
            f"✅ [{std_tag}] {_style_label(style)} → {layer.name()} "
            f"[{field_name}] — {len(new_cats)}/{total} categories  "
            f"(QML: {style['qml']})"
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







