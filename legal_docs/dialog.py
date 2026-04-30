# -*- coding: utf-8 -*-
"""LVT4U — Legal Documents Library.

Categorized viewer for Vietnamese forestry legal documents,
TCVN standards, and regulatory circulars. Opens files with
the system's default application.

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""

import os

from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QFont
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QScrollArea, QFrame, QMessageBox,
)

from ..shared.i18n import tr, current_language

_DOCS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), os.pardir, "docs")
)

# ── Document catalog ──────────────────────────────────────────────────
# Each category: (tab_icon, tab_label_vi, tab_label_en, docs_list)
# Each doc: (filename, vi_title, en_title)
_CATALOG = [
    {
        "icon": "📜",
        "vi": "Thông tư",
        "en": "Circulars",
        "docs": [
            ("TT16_2023_BNN.pdf",
             "TT 16/2023/TT-BNNPTNT — Phân loại đất, rừng (bản ký)",
             "Circular 16/2023 — Land & forest classification (signed)"),
            ("TT16_PhuLuc_45_46.doc",
             "TT 16 — Phụ lục 45 + 46",
             "Circular 16 — Appendix 45 + 46"),
            ("TT16_PhuLuc_47_48.doc",
             "TT 16 — Phụ lục 47 + 48",
             "Circular 16 — Appendix 47 + 48"),
            ("TT25_2009_ThongKe_KiemKeRung.doc",
             "TT 25/2009 — Thống kê, kiểm kê rừng & lập hồ sơ quản lý rừng",
             "Circular 25/2009 — Forest inventory & management dossier"),
            ("TT33_2018_DieuTraRung.doc",
             "TT 33/2018 — Điều tra rừng",
             "Circular 33/2018 — Forest investigation"),
            ("TT34_2009_PhanLoaiRung_VI.doc",
             "TT 34/2009 — Tiêu chí xác định và phân loại rừng (VN)",
             "Circular 34/2009 — Forest classification criteria (Vietnamese)"),
            ("TT34_2009_PhanLoaiRung_EN.doc",
             "TT 34/2009 — Tiêu chí xác định và phân loại rừng (EN)",
             "Circular 34/2009 — Forest classification criteria (English)"),
        ],
    },
    {
        "icon": "🗺️",
        "vi": "Bản đồ lâm nghiệp",
        "en": "Forestry Maps",
        "docs": [
            ("TCVN_11565_2016_BanDo_HienTrangRung.pdf",
             "TCVN 11565:2016 — Bản đồ hiện trạng rừng",
             "TCVN 11565:2016 — Forest status map standard"),
            ("TCVN_11566_2016_BanDo_QuyHoachLamNghiep.pdf",
             "TCVN 11566:2016 — Bản đồ quy hoạch lâm nghiệp",
             "TCVN 11566:2016 — Forestry planning map standard"),
        ],
    },
    {
        "icon": "🌲",
        "vi": "Rừng trồng",
        "en": "Plantation Standards",
        "docs": [
            ("TCVN_11567_1_2016_RungTrong_Phan1.pdf",
             "TCVN 11567-1:2016 — Rừng trồng — Phần 1",
             "TCVN 11567-1:2016 — Plantation forest — Part 1"),
            ("TCVN_11567_2_2016_RungTrong_Phan2.pdf",
             "TCVN 11567-2:2016 — Rừng trồng — Phần 2",
             "TCVN 11567-2:2016 — Plantation forest — Part 2"),
            ("TCVN_12509_2018_RungTrong_SauKienThiet.doc",
             "TCVN 12509-1:2018 — Rừng trồng sau thời gian kiến thiết cơ bản",
             "TCVN 12509-1:2018 — Plantation after basic construction"),
        ],
    },
    {
        "icon": "🔥",
        "vi": "Phòng cháy rừng",
        "en": "Forest Fire Prevention",
        "docs": [
            ("TCVN_14274_2025_PhongChayRung.pdf",
             "TCVN 14274:2025 — Phòng cháy chữa cháy rừng",
             "TCVN 14274:2025 — Forest fire prevention standard"),
            ("TCVN_2025_CapDuBao_ChayRung.pdf",
             "TCVN 2025 — Cấp dự báo cháy rừng",
             "TCVN 2025 — Forest fire forecast classification"),
        ],
    },
    {
        "icon": "📋",
        "vi": "Quyết định & Tiêu chuẩn khác",
        "en": "Decisions & Other Standards",
        "docs": [
            ("QD_04_2004_QuyCheKhaiThacGo.doc",
             "QĐ 04/2004 — Quy chế khai thác gỗ",
             "Decision 04/2004 — Timber exploitation regulations"),
            ("QD_4215_BKHCN_CongBo_TCVN.doc",
             "QĐ 4215/BKHCN — Công bố TCVN về lâm nghiệp",
             "Decision 4215/MOST — TCVN forestry standards publication"),
            ("TCN_74_2006_PhanLoaiGoTron.doc",
             "04 TCN 74:2006 — Phân loại gỗ tròn",
             "04 TCN 74:2006 — Round timber classification"),
            ("TCN_126_2006_TrongCayGoLon.doc",
             "04 TCN 126:2006 — Hướng dẫn kỹ thuật trồng cây gỗ lớn",
             "04 TCN 126:2006 — Large timber planting technical guide"),
            ("TCN_132_2006_SinhTruong_KeoLai.doc",
             "04 TCN 132:2006 — Biểu sinh trưởng rừng keo lai",
             "04 TCN 132:2006 — Acacia hybrid growth tables"),
            ("TCVN_13353_2021_LamNghiep.doc",
             "TCVN 13353:2021 — Tiêu chuẩn lâm nghiệp",
             "TCVN 13353:2021 — Forestry standard"),
            ("DanhMuc_TieuChuan_LamNghiep.pdf",
             "Danh mục tiêu chuẩn Việt Nam về lâm nghiệp",
             "Catalog of Vietnamese forestry standards"),
        ],
    },
]


class LegalDocsDialog(QDialog):
    """Categorized Legal Documents Library dialog."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("LVT4U — " + tr("Legal Documents"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(680)
        self.setMinimumHeight(520)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # Header
        hdr = QLabel("📚  " + tr("Legal Documents"))
        hdr.setFont(QFont("Segoe UI", 14, QFont.Bold))
        hdr.setStyleSheet("color:#5d4037; padding:4px;")
        root.addWidget(hdr)

        lang = current_language()

        # Count
        total = sum(len(cat["docs"]) for cat in _CATALOG)
        subtitle = (
            f"Thư viện {total} văn bản pháp lý ngành lâm nghiệp Việt Nam"
            if lang == "vi" else
            f"Library of {total} Vietnamese forestry legal documents"
        )
        sub = QLabel(subtitle)
        sub.setStyleSheet("color:#888; font-size:11px; padding:0 4px 4px 4px;")
        root.addWidget(sub)

        # Tabs
        tabs = QTabWidget()
        root.addWidget(tabs, 1)

        for cat in _CATALOG:
            tab_title = f'{cat["icon"]} {cat[lang]}'
            tab = QWidget()
            tabs.addTab(tab, tab_title)
            self._build_doc_list(tab, cat["docs"], lang)

        # Close button
        btn_close = QPushButton(tr("Close"))
        btn_close.setMinimumHeight(36)
        btn_close.setStyleSheet(
            "QPushButton{background:#757575;color:white;border-radius:5px;"
            "padding:6px 20px;}"
            "QPushButton:hover{background:#616161;}"
        )
        btn_close.clicked.connect(self.close)
        root.addWidget(btn_close)

    def _build_doc_list(self, parent, docs, lang):
        ly = QVBoxLayout(parent)
        ly.setSpacing(0)
        ly.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        inner = QVBoxLayout(container)
        inner.setSpacing(6)

        for filename, vi_title, en_title in docs:
            title = vi_title if lang == "vi" else en_title
            filepath = os.path.join(_DOCS_DIR, filename)
            exists = os.path.isfile(filepath)

            # Extension badge
            ext = os.path.splitext(filename)[1].upper().replace(".", "")
            ext_icon = "📄" if ext == "PDF" else "📝"

            btn = QPushButton(f"{ext_icon}  {title}")
            btn.setFont(QFont("Segoe UI", 10))
            btn.setMinimumHeight(38)
            btn.setCursor(Qt.PointingHandCursor)

            if exists:
                btn.setStyleSheet(
                    "QPushButton{text-align:left;padding:6px 12px;"
                    "background:#fff8e1;border:1px solid #ffe082;"
                    "border-radius:4px;}"
                    "QPushButton:hover{background:#fff3c4;"
                    "border-color:#ffc107;}"
                )
                btn.setToolTip(filename)
                btn.clicked.connect(
                    lambda checked, f=filepath: self._open_file(f)
                )
            else:
                btn.setStyleSheet(
                    "QPushButton{text-align:left;padding:6px 12px;"
                    "background:#f5f5f5;color:#aaa;border:1px solid #ddd;"
                    "border-radius:4px;}"
                )
                btn.setToolTip(f"File not found: {filename}")
                btn.setEnabled(False)

            inner.addWidget(btn)

        inner.addStretch()
        scroll.setWidget(container)
        ly.addWidget(scroll)

    @staticmethod
    def _open_file(filepath):
        """Open a file with the system's default application."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
