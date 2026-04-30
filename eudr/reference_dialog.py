# -*- coding: utf-8 -*-
"""
LVT EUDR Module — Reference Documents Dialog.

Displays EUDR regulatory documents and guides in English/Vietnamese.

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""

from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QFont, QDesktopServices
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextBrowser, QTabWidget, QWidget,
)


# Reference documents data
_REFERENCES = [
    {
        "title_en": "EU Regulation 2023/1115 (EUDR) — Full Text",
        "title_vi": "Quy định EU 2023/1115 (EUDR) — Toàn văn",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R1115",
        "desc_en": "The European Union Deforestation Regulation. Official legal text published in the Official Journal of the EU.",
        "desc_vi": "Quy định Chống phá rừng của Liên minh Châu Âu. Văn bản pháp lý chính thức đăng trên Công báo EU.",
    },
    {
        "title_en": "EUDR FAQ — European Commission",
        "title_vi": "Hỏi đáp EUDR — Ủy ban Châu Âu",
        "url": "https://environment.ec.europa.eu/topics/forests/deforestation/regulation-deforestation-free-products_en",
        "desc_en": "Official FAQ and guidance documents from the European Commission on implementing the EUDR.",
        "desc_vi": "Hỏi đáp và tài liệu hướng dẫn chính thức từ Ủy ban Châu Âu về triển khai EUDR.",
    },
    {
        "title_en": "GeoJSON RFC 7946 — Specification",
        "title_vi": "GeoJSON RFC 7946 — Đặc tả kỹ thuật",
        "url": "https://tools.ietf.org/html/rfc7946",
        "desc_en": "The GeoJSON format specification (RFC 7946). EUDR requires geolocation data in GeoJSON format with WGS84 coordinates.",
        "desc_vi": "Đặc tả định dạng GeoJSON (RFC 7946). EUDR yêu cầu dữ liệu vị trí địa lý ở định dạng GeoJSON với tọa độ WGS84.",
    },
    {
        "title_en": "EPSG:4326 — WGS84 Geodetic CRS",
        "title_vi": "EPSG:4326 — Hệ tọa độ WGS84",
        "url": "https://epsg.io/4326",
        "desc_en": "WGS84 coordinate reference system. EUDR mandates all geolocation data use EPSG:4326 with ≥6 decimal precision.",
        "desc_vi": "Hệ tọa độ tham chiếu WGS84. EUDR bắt buộc tất cả dữ liệu vị trí sử dụng EPSG:4326 với ≥6 chữ số thập phân.",
    },
    {
        "title_en": "EUDR Information System — EU DDS Portal",
        "title_vi": "Hệ thống thông tin EUDR — Cổng EU DDS",
        "url": "https://environment.ec.europa.eu/topics/forests/deforestation/regulation-deforestation-free-products/information-system_en",
        "desc_en": "The EU Due Diligence System (DDS) portal where operators submit due diligence statements.",
        "desc_vi": "Cổng Hệ thống Thẩm định (DDS) của EU, nơi doanh nghiệp nộp báo cáo thẩm định.",
    },
    {
        "title_en": "Commodities Covered by EUDR",
        "title_vi": "Các mặt hàng thuộc phạm vi EUDR",
        "url": "https://environment.ec.europa.eu/topics/forests/deforestation/regulation-deforestation-free-products_en",
        "desc_en": "Cattle, cocoa, coffee, oil palm, rubber, soya, wood — and derived products. Full list in Annex I of the Regulation.",
        "desc_vi": "Gia súc, ca cao, cà phê, dầu cọ, cao su, đậu nành, gỗ — và các sản phẩm phái sinh. Danh sách đầy đủ tại Phụ lục I.",
    },
    {
        "title_en": "EUDR Geolocation Requirements — Technical Guide",
        "title_vi": "Yêu cầu Vị trí Địa lý EUDR — Hướng dẫn Kỹ thuật",
        "url": "https://environment.ec.europa.eu/topics/forests/deforestation/regulation-deforestation-free-products_en",
        "desc_en": (
            "Technical requirements:\n"
            "• Plots ≤ 4 ha: single point (latitude/longitude)\n"
            "• Plots > 4 ha: polygon boundary (closed, non-self-intersecting)\n"
            "• CRS: WGS84 (EPSG:4326)\n"
            "• Precision: ≥ 6 decimal digits\n"
            "• File format: GeoJSON\n"
            "• Max file size: 25 MB"
        ),
        "desc_vi": (
            "Yêu cầu kỹ thuật:\n"
            "• Lô ≤ 4 ha: một điểm (latitude/longitude)\n"
            "• Lô > 4 ha: ranh giới đa giác (đóng kín, không tự cắt)\n"
            "• Hệ tọa độ: WGS84 (EPSG:4326)\n"
            "• Độ chính xác: ≥ 6 chữ số thập phân\n"
            "• Định dạng: GeoJSON\n"
            "• Kích thước tối đa: 25 MB"
        ),
    },
    {
        "title_en": "Vietnam Forestry & EUDR Compliance",
        "title_vi": "Lâm nghiệp Việt Nam & Tuân thủ EUDR",
        "url": "https://www.euflegt.efi.int/vietnam",
        "desc_en": "Vietnam is a key exporter of wood products to the EU. Resources on VPA/FLEGT and EUDR compliance for Vietnamese operators.",
        "desc_vi": "Việt Nam là nước xuất khẩu gỗ chủ lực sang EU. Tài liệu về VPA/FLEGT và tuân thủ EUDR cho doanh nghiệp Việt Nam.",
    },
]


class EudrReferenceDialog(QDialog):
    """Dialog showing EUDR reference documents in EN/VI."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.lang = 'vi'
        self.setMinimumSize(700, 550)
        self.resize(750, 600)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        self._setup_ui()
        self._refresh_ui_text()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Top bar
        top = QHBoxLayout()
        self.btn_lang = QPushButton()
        self.btn_lang.setFixedWidth(110)
        self.btn_lang.clicked.connect(self._toggle_language)
        top.addWidget(self.btn_lang)
        top.addStretch()
        layout.addLayout(top)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Reference list
        self.tab_refs = QWidget()
        self._setup_refs_tab()
        self.tabs.addTab(self.tab_refs, "")

        # Tab 2: EUDR Summary
        self.tab_summary = QWidget()
        self._setup_summary_tab()
        self.tabs.addTab(self.tab_summary, "")

        # Close
        btn_ly = QHBoxLayout()
        btn_ly.addStretch()
        self.btn_close = QPushButton()
        self.btn_close.clicked.connect(self.close)
        btn_ly.addWidget(self.btn_close)
        layout.addLayout(btn_ly)

    def _setup_refs_tab(self):
        layout = QVBoxLayout(self.tab_refs)
        self.txt_refs = QTextBrowser()
        self.txt_refs.setOpenExternalLinks(True)
        layout.addWidget(self.txt_refs)

    def _setup_summary_tab(self):
        layout = QVBoxLayout(self.tab_summary)
        self.txt_summary = QTextBrowser()
        self.txt_summary.setOpenExternalLinks(True)
        layout.addWidget(self.txt_summary)

    def _toggle_language(self):
        self.lang = 'en' if self.lang == 'vi' else 'vi'
        self._refresh_ui_text()

    def _refresh_ui_text(self):
        is_vi = self.lang == 'vi'
        self.setWindowTitle(
            "LVT — " + ("Tài liệu tham khảo EUDR" if is_vi
                         else "EUDR Reference Documents")
        )
        self.btn_lang.setText(
            "🌐 English" if is_vi else "🌐 Tiếng Việt"
        )
        self.tabs.setTabText(
            0, "Tài liệu tham khảo" if is_vi else "References"
        )
        self.tabs.setTabText(
            1, "Tóm tắt EUDR" if is_vi else "EUDR Summary"
        )
        self.btn_close.setText("Đóng" if is_vi else "Close")

        self._render_refs()
        self._render_summary()

    def _render_refs(self):
        is_vi = self.lang == 'vi'
        html = "<div style='font-family:Arial;padding:5px;'>"
        html += (
            "<h2 style='color:#1B5E20;'>"
            + ("📚 Tài liệu tham khảo EUDR" if is_vi
               else "📚 EUDR Reference Documents")
            + "</h2>"
        )

        for i, ref in enumerate(_REFERENCES, 1):
            title = ref['title_vi'] if is_vi else ref['title_en']
            desc = ref['desc_vi'] if is_vi else ref['desc_en']
            url = ref['url']
            desc_html = desc.replace('\n', '<br>')

            html += f"""
            <div style='margin:10px 0;padding:12px;background:#f9f9f9;
            border-radius:6px;border-left:4px solid #1B5E20;'>
                <h3 style='margin:0 0 5px 0;color:#1B5E20;'>
                    {i}. {title}
                </h3>
                <p style='margin:5px 0;font-size:13px;color:#444;
                line-height:1.6;'>{desc_html}</p>
                <a href='{url}' style='color:#1565C0;font-size:12px;
                text-decoration:none;'>🔗 {url}</a>
            </div>
            """

        html += "</div>"
        self.txt_refs.setHtml(html)

    def _render_summary(self):
        is_vi = self.lang == 'vi'
        if is_vi:
            html = """
            <div style='font-family:Arial;padding:10px;'>
            <div style='background-color:#1B5E20;
            color:white;padding:16px 20px;border-radius:8px;margin-bottom:14px;
            text-align:center;font-size:15px;line-height:1.8;'>
            🌿 <b><i>"Hãy chứng minh cho tôi sản phẩm của bạn
            đến từ polygon xinh đẹp đó"</i></b> 🌿
            </div>
            <h2 style='color:#1B5E20;'>📋 Tóm tắt Quy định EUDR</h2>

            <h3>Quy định EU 2023/1115 là gì?</h3>
            <p>Quy định Chống phá rừng của EU (EUDR) yêu cầu các doanh nghiệp
            đặt sản phẩm lên thị trường EU phải chứng minh rằng sản phẩm
            không gây ra phá rừng hoặc suy thoái rừng.</p>

            <h3>Các mặt hàng thuộc phạm vi:</h3>
            <ul>
                <li>🌲 <b>Gỗ</b> và sản phẩm gỗ</li>
                <li>☕ <b>Cà phê</b></li>
                <li>🍫 <b>Ca cao</b></li>
                <li>🌴 <b>Dầu cọ</b></li>
                <li>🌱 <b>Đậu nành</b></li>
                <li>🐄 <b>Gia súc</b></li>
                <li>🏭 <b>Cao su</b></li>
            </ul>

            <h3>Yêu cầu về dữ liệu vị trí:</h3>
            <table border='1' cellpadding='8'
            style='border-collapse:collapse;width:100%;'>
                <tr style='background:#1B5E20;color:white;'>
                    <th>Tiêu chí</th><th>Yêu cầu</th>
                </tr>
                <tr><td>Hệ tọa độ</td><td>WGS84 (EPSG:4326)</td></tr>
                <tr><td>Độ chính xác</td><td>≥ 6 chữ số thập phân</td></tr>
                <tr><td>Lô ≤ 4 ha</td><td>Một điểm (lat/lon)</td></tr>
                <tr><td>Lô > 4 ha</td><td>Đa giác (polygon)</td></tr>
                <tr><td>Đa giác</td><td>Đóng kín, không tự cắt</td></tr>
                <tr><td>Định dạng</td><td>GeoJSON</td></tr>
                <tr><td>Kích thước</td><td>≤ 25 MB</td></tr>
            </table>

            <h3>Mốc thời gian quan trọng:</h3>
            <ul>
                <li><b>29/06/2023:</b> Quy định có hiệu lực</li>
                <li><b>30/12/2025:</b> Áp dụng cho doanh nghiệp lớn</li>
                <li><b>30/06/2026:</b> Áp dụng cho doanh nghiệp vừa & nhỏ</li>
            </ul>

            <div style='margin-top:15px;padding:12px;background:#E8F5E9;
            border-radius:6px;border-left:4px solid #1B5E20;'>
            <b>💡 Lưu ý:</b> Plugin LVT hỗ trợ xuất GeoJSON đúng chuẩn EUDR,
            tự động chuyển đổi hệ tọa độ, kiểm tra và sửa lỗi hình học.
            </div>
            </div>
            """
        else:
            html = """
            <div style='font-family:Arial;padding:10px;'>
            <div style='background-color:#1B5E20;
            color:white;padding:16px 20px;border-radius:8px;margin-bottom:14px;
            text-align:center;font-size:15px;line-height:1.8;'>
            🌿 <b><i>"Prove to me that your product
            comes from that beautiful polygon"</i></b> 🌿
            </div>
            <h2 style='color:#1B5E20;'>📋 EUDR Regulation Summary</h2>

            <h3>What is EU Regulation 2023/1115?</h3>
            <p>The EU Deforestation Regulation (EUDR) requires operators placing
            products on the EU market to prove that products are
            deforestation-free and have not caused forest degradation.</p>

            <h3>Commodities in scope:</h3>
            <ul>
                <li>🌲 <b>Wood</b> and wood products</li>
                <li>☕ <b>Coffee</b></li>
                <li>🍫 <b>Cocoa</b></li>
                <li>🌴 <b>Oil palm</b></li>
                <li>🌱 <b>Soya</b></li>
                <li>🐄 <b>Cattle</b></li>
                <li>🏭 <b>Rubber</b></li>
            </ul>

            <h3>Geolocation requirements:</h3>
            <table border='1' cellpadding='8'
            style='border-collapse:collapse;width:100%;'>
                <tr style='background:#1B5E20;color:white;'>
                    <th>Criteria</th><th>Requirement</th>
                </tr>
                <tr><td>CRS</td><td>WGS84 (EPSG:4326)</td></tr>
                <tr><td>Precision</td><td>≥ 6 decimal digits</td></tr>
                <tr><td>Plots ≤ 4 ha</td><td>Single point (lat/lon)</td></tr>
                <tr><td>Plots > 4 ha</td><td>Polygon boundary</td></tr>
                <tr><td>Polygons</td><td>Closed, non-self-intersecting</td></tr>
                <tr><td>Format</td><td>GeoJSON</td></tr>
                <tr><td>File size</td><td>≤ 25 MB</td></tr>
            </table>

            <h3>Key dates:</h3>
            <ul>
                <li><b>29/06/2023:</b> Regulation enters into force</li>
                <li><b>30/12/2025:</b> Applies to large operators</li>
                <li><b>30/06/2026:</b> Applies to SMEs</li>
            </ul>

            <div style='margin-top:15px;padding:12px;background:#E8F5E9;
            border-radius:6px;border-left:4px solid #1B5E20;'>
            <b>💡 Note:</b> The LVT plugin exports EUDR-compliant GeoJSON,
            with automatic CRS transformation and geometry validation/repair.
            </div>
            </div>
            """
        self.txt_summary.setHtml(html)
