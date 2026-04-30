# -*- coding: utf-8 -*-
"""
LVT CRS Tools — Set CRS, Reproject/Export, VN-2000 Catalog.

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""
import os
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QDesktopServices
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QFormLayout, QTabWidget, QWidget,
    QMessageBox, QFileDialog, QScrollArea, QTextBrowser,
)
from qgis.core import (
    QgsProject, QgsCoordinateReferenceSystem, QgsVectorLayer,
    QgsVectorFileWriter, QgsCoordinateTransformContext,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtCore import QUrl

from ..shared.i18n import current_language
from .._crs_list import CRS_LIST


class CrsToolsDialog(QDialog):
    """Unified CRS Tools: Set CRS, Reproject/Export, VN-2000 Catalog."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.lang = current_language()
        self.setMinimumSize(720, 580)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()
        self._refresh_text()

    def _setup_ui(self):
        ly = QVBoxLayout(self)

        # Current CRS info
        self.lbl_current = QLabel()
        self.lbl_current.setStyleSheet(
            "padding:8px;border:1px solid #999;border-radius:4px;"
            "font-size:12px;font-weight:bold"
        )
        self.lbl_current.setWordWrap(True)
        ly.addWidget(self.lbl_current)

        # Language toggle
        btn_row = QHBoxLayout()
        self.btn_lang = QPushButton()
        self.btn_lang.setFixedWidth(120)
        self.btn_lang.clicked.connect(self._toggle_lang)
        btn_row.addWidget(self.btn_lang)
        btn_row.addStretch()
        ly.addLayout(btn_row)

        # Tabs
        self.tabs = QTabWidget()
        ly.addWidget(self.tabs)

        # Tab 1: Set Project CRS
        self.tab_set = QWidget()
        self._build_set_tab()
        self.tabs.addTab(self.tab_set, "")

        # Tab 2: Reproject / Export
        self.tab_reproject = QWidget()
        self._build_reproject_tab()
        self.tabs.addTab(self.tab_reproject, "")

        # Tab 3: VN-2000 Catalog (34 new)
        self.tab_catalog = QWidget()
        self._build_catalog_tab()
        self.tabs.addTab(self.tab_catalog, "")

        # Tab 4: Notes
        self.tab_notes = QWidget()
        self._build_notes_tab()
        self.tabs.addTab(self.tab_notes, "")

        # Close
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        ly.addWidget(btn_close)

    def _build_set_tab(self):
        ly = QVBoxLayout(self.tab_set)
        ly.addWidget(QLabel("<b>⚙️ Set Project CRS / Đặt CRS cho dự án</b>"))
        ly.addWidget(QLabel(
            "Chỉ gán nhãn hệ tọa độ cho dự án — KHÔNG chuyển đổi tọa độ dữ liệu."
        ))

        form = QFormLayout()
        self.cmb_set = QComboBox()
        for label, _ in CRS_LIST:
            self.cmb_set.addItem(label)
        for i, (_, code) in enumerate(CRS_LIST):
            if not code:
                self.cmb_set.model().item(i).setEnabled(False)
        form.addRow("CRS:", self.cmb_set)
        ly.addLayout(form)

        self.btn_set = QPushButton("✅ Apply / Áp dụng")
        self.btn_set.setStyleSheet(
            "QPushButton{background:#2e7d32;color:#fff;font-weight:bold;"
            "padding:8px 20px;border-radius:4px}"
            "QPushButton:hover{background:#388e3c}"
        )
        self.btn_set.clicked.connect(self._do_set_crs)
        ly.addWidget(self.btn_set)
        ly.addStretch()

    def _build_reproject_tab(self):
        ly = QVBoxLayout(self.tab_reproject)
        ly.addWidget(QLabel(
            "<b>🔄 Reproject & Export / Chuyển đổi hệ tọa độ & Xuất file</b>"
        ))
        ly.addWidget(QLabel(
            "Chuyển đổi thực sự tọa độ của layer sang CRS mới và lưu ra Shapefile."
        ))

        form = QFormLayout()
        self.cmb_layer = QgsMapLayerComboBox()
        self.cmb_layer.setFilters(
            self.cmb_layer.filters() | 0x1  # VectorLayer
        )
        form.addRow("Layer:", self.cmb_layer)

        self.cmb_target = QComboBox()
        for label, _ in CRS_LIST:
            self.cmb_target.addItem(label)
        for i, (_, code) in enumerate(CRS_LIST):
            if not code:
                self.cmb_target.model().item(i).setEnabled(False)
        form.addRow("Target CRS:", self.cmb_target)
        ly.addLayout(form)

        self.btn_export = QPushButton("💾 Export Shapefile")
        self.btn_export.setStyleSheet(
            "QPushButton{background:#1565c0;color:#fff;font-weight:bold;"
            "padding:8px 20px;border-radius:4px}"
            "QPushButton:hover{background:#1976d2}"
        )
        self.btn_export.clicked.connect(self._do_reproject)
        ly.addWidget(self.btn_export)
        ly.addStretch()

    def _build_catalog_tab(self):
        ly = QVBoxLayout(self.tab_catalog)
        self.catalog_browser = QTextBrowser()
        self.catalog_browser.setOpenExternalLinks(True)
        ly.addWidget(self.catalog_browser)

    def _build_notes_tab(self):
        ly = QVBoxLayout(self.tab_notes)
        self.notes_browser = QTextBrowser()
        self.notes_browser.setOpenExternalLinks(True)
        ly.addWidget(self.notes_browser)

    # --- Actions ---
    def _do_set_crs(self):
        idx = self.cmb_set.currentIndex()
        code = CRS_LIST[idx][1]
        if not code:
            return
        crs = QgsCoordinateReferenceSystem(code)
        if not crs.isValid():
            QMessageBox.warning(self, "LVT", f"Invalid CRS: {code}")
            return
        QgsProject.instance().setCrs(crs)
        self._update_current()
        QMessageBox.information(
            self, "✅ CRS Updated",
            f"Project CRS → {crs.authid()} — {crs.description()}"
        )

    def _do_reproject(self):
        layer = self.cmb_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, "LVT", "No layer selected.")
            return
        idx = self.cmb_target.currentIndex()
        code = CRS_LIST[idx][1]
        if not code:
            return
        target_crs = QgsCoordinateReferenceSystem(code)
        if not target_crs.isValid():
            QMessageBox.warning(self, "LVT", f"Invalid CRS: {code}")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Shapefile", "", "Shapefile (*.shp)"
        )
        if not path:
            return

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        ctx = QgsCoordinateTransformContext()
        ctx.addCoordinateOperation(layer.crs(), target_crs, "")

        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, path, ctx, options
        )
        if error[0] == QgsVectorFileWriter.NoError:
            new_layer = QgsVectorLayer(path, os.path.basename(path), "ogr")
            if new_layer.isValid():
                QgsProject.instance().addMapLayer(new_layer)
            QMessageBox.information(
                self, "✅ Export OK",
                f"Exported to {os.path.basename(path)}\nCRS: {target_crs.authid()}"
            )
        else:
            QMessageBox.critical(self, "Export Error", str(error))

    # --- Language ---
    def _toggle_lang(self):
        self.lang = 'en' if self.lang == 'vi' else 'vi'
        self._refresh_text()

    def _update_current(self):
        crs = QgsProject.instance().crs()
        self.lbl_current.setText(
            f"📍 Current / Hiện tại: <b>{crs.authid()}</b> — {crs.description()}"
        )
        # Sync combo
        for i, (_, code) in enumerate(CRS_LIST):
            if code == crs.authid():
                self.cmb_set.setCurrentIndex(i)
                break

    def _refresh_text(self):
        vi = self.lang == 'vi'
        self.setWindowTitle(
            "LVT — Hệ tọa độ / CRS Tools" if vi else "LVT — CRS Tools"
        )
        self.btn_lang.setText("🇬🇧 English" if vi else "🇻🇳 Tiếng Việt")
        self.tabs.setTabText(0, "⚙️ Set CRS" if not vi else "⚙️ Đặt CRS")
        self.tabs.setTabText(1, "🔄 Reproject" if not vi else "🔄 Chuyển đổi")
        self.tabs.setTabText(2, "📋 VN-2000" if not vi else "📋 VN-2000")
        self.tabs.setTabText(3, "📖 Notes" if not vi else "📖 Ghi chú")
        self._update_current()
        self._render_catalog()
        self._render_notes()

    def _render_catalog(self):
        self.catalog_browser.setHtml(
            self._catalog_vn() if self.lang == 'vi' else self._catalog_en()
        )

    def _render_notes(self):
        self.notes_browser.setHtml(
            self._notes_vn() if self.lang == 'vi' else self._notes_en()
        )

    def refresh_layers(self):
        pass

    # --- Catalog HTML ---
    def _catalog_en(self):
        return """
<div style='font-family:Arial;font-size:12px;padding:8px'>
<h2 style='color:#1B5E20'>🌐 VN-2000 CRS Catalog — 34 Provinces (New)</h2>
<p>Quick EPSG reference for Vietnamese forestry & environmental mapping.</p>
<h3>🔵 Global / WGS 84</h3>
<table border='1' cellpadding='4' style='border-collapse:collapse;width:100%'>
<tr style='background:#e3f2fd'><th>EPSG</th><th>Name</th><th>Type</th><th>Description</th></tr>
<tr><td><b>4326</b></td><td>WGS 84</td><td>Geographic</td><td>Global (GPS). Lat/Lon degrees.</td></tr>
<tr><td><b>32648</b></td><td>UTM 48N</td><td>Projected</td><td>West Vietnam. Meters.</td></tr>
<tr><td><b>32649</b></td><td>UTM 49N</td><td>Projected</td><td>East Vietnam. Meters.</td></tr>
</table>
<h3>🟢 VN-2000 — 6° Zones</h3>
<table border='1' cellpadding='4' style='border-collapse:collapse;width:100%'>
<tr style='background:#e8f5e9'><th>EPSG</th><th>Name</th><th>CM</th><th>Coverage</th></tr>
<tr><td><b>3405</b></td><td>VN-2000 / 48N</td><td>105°E</td><td>West Vietnam</td></tr>
<tr><td><b>3406</b></td><td>VN-2000 / 49N</td><td>111°E</td><td>East Vietnam</td></tr>
</table>
<h3>🟡 VN-2000 — 3° Zones (34 Provinces)</h3>
<table border='1' cellpadding='3' style='border-collapse:collapse;width:100%;font-size:11px'>
<tr style='background:#fff9c4'><th>CM</th><th>EPSG</th><th>Province (New)</th><th>Merged From</th></tr>
<tr><td>103°00'</td><td>9205</td><td>Điện Biên</td><td>—</td></tr>
<tr><td>104°00'</td><td>9206</td><td>Sơn La</td><td>—</td></tr>
<tr><td>104°30'</td><td>9207</td><td>Cà Mau</td><td>Bạc Liêu + Cà Mau</td></tr>
<tr><td>104°45'</td><td>9208</td><td>An Giang, Lai Châu, Lào Cai, Nghệ An, Phú Thọ</td>
<td>Kiên Giang+An Giang, Lào Cai+Yên Bái, Hòa Bình+Vĩnh Phúc+Phú Thọ</td></tr>
<tr><td>105°00'</td><td>5896</td><td>Hà Nội, Thanh Hóa, Ninh Bình, Đồng Tháp, Cần Thơ</td>
<td>Hà Nam+Nam Định+Ninh Bình, Tiền Giang+Đồng Tháp, Sóc Trăng+Hậu Giang+Cần Thơ</td></tr>
<tr><td>105°30'</td><td>9209</td><td>Hà Tĩnh, Hưng Yên, Vĩnh Long</td>
<td>Hưng Yên+Thái Bình, Bến Tre+Vĩnh Long+Trà Vinh</td></tr>
<tr><td>105°45'</td><td>9210</td><td>Cao Bằng, Tây Ninh, Hải Phòng, TP HCM</td>
<td>Tây Ninh+Long An, Hải Phòng+Hải Dương, Bà Rịa-VT+Bình Dương+TP HCM</td></tr>
<tr><td>106°00'</td><td>9211</td><td>Quảng Trị, Tuyên Quang</td>
<td>Quảng Bình+Quảng Trị, Hà Giang+Tuyên Quang</td></tr>
<tr><td>106°30'</td><td>9213</td><td>Thái Nguyên</td><td>Thái Nguyên+Bắc Kạn</td></tr>
<tr><td>107°00'</td><td>9214</td><td>Bắc Ninh, TP Huế</td><td>Bắc Ninh+Bắc Giang</td></tr>
<tr><td>107°15'</td><td>9215</td><td>Lạng Sơn</td><td>—</td></tr>
<tr><td>107°45'</td><td>5899</td><td>Quảng Ninh, Đồng Nai, Lâm Đồng, Đà Nẵng</td>
<td>Bình Phước+Đồng Nai, Đắk Nông+Bình Thuận+Lâm Đồng, Quảng Nam+Đà Nẵng</td></tr>
<tr><td>108°00'</td><td>9216</td><td>Quảng Ngãi</td><td>Kon Tum+Quảng Ngãi</td></tr>
<tr><td>108°15'</td><td>9217</td><td>Gia Lai, Khánh Hòa</td><td>Gia Lai+Bình Định, Ninh Thuận+Khánh Hòa</td></tr>
<tr><td>108°30'</td><td>9218</td><td>Đắk Lắk</td><td>Phú Yên+Đắk Lắk</td></tr>
</table>
</div>"""

    def _catalog_vn(self):
        return self._catalog_en().replace(
            "VN-2000 CRS Catalog — 34 Provinces (New)",
            "Thư viện CRS VN-2000 — 34 Tỉnh (Mới)"
        ).replace(
            "Quick EPSG reference for Vietnamese forestry & environmental mapping.",
            "Tra cứu nhanh mã EPSG dùng trong lâm nghiệp & môi trường Việt Nam."
        )

    # --- Notes HTML ---
    def _notes_en(self):
        return """
<div style='font-family:Arial;font-size:12px;padding:8px'>
<h2 style='color:#1B5E20'>📖 CRS Notes — Understanding Coordinate Systems</h2>

<h3>🔹 What is a CRS?</h3>
<p>A <b>Coordinate Reference System (CRS)</b> defines how coordinates
(numbers) map to real locations on Earth. Without a CRS, your data is
just numbers with no geographic meaning.</p>

<h3>🔹 Set CRS vs. Reproject — The Key Difference</h3>
<table border='1' cellpadding='6' style='border-collapse:collapse;width:100%'>
<tr style='background:#e3f2fd'><th width='30%'>Action</th><th>What happens</th><th>When to use</th></tr>
<tr><td><b>⚙️ Set CRS</b></td>
<td>Only <b>changes the label</b>. The coordinates stay the same.
Like putting a new sticker on a box — contents unchanged.</td>
<td>Your data has the WRONG CRS label assigned (e.g., meters labeled as degrees).</td></tr>
<tr><td><b>🔄 Reproject</b></td>
<td><b>Transforms every coordinate</b> from one system to another.
Physically recalculates X, Y values.</td>
<td>You need to deliver data in a different CRS (e.g., VN-2000 → WGS 84).</td></tr>
</table>

<div style='background:#FFF3E0;padding:10px;border-left:4px solid #FF9800;margin:10px 0'>
<b>⚠️ Warning:</b> If you "Set CRS" when you should "Reproject",
your data will appear in the wrong location on the map!
</div>

<h3>🔹 Geographic vs. Projected CRS</h3>
<table border='1' cellpadding='6' style='border-collapse:collapse;width:100%'>
<tr style='background:#E8F5E9'><th></th><th>Geographic (EPSG:4326)</th><th>Projected (VN-2000, UTM)</th></tr>
<tr><td><b>Unit</b></td><td>Degrees (°)</td><td>Meters (m)</td></tr>
<tr><td><b>Coordinates</b></td><td>Lat 16.05°, Lon 108.2°</td><td>X 583204, Y 1774521</td></tr>
<tr><td><b>Best for</b></td><td>GPS, web maps, global view</td><td>Area/distance calculations, cadastral</td></tr>
</table>

<h3>🔹 VN-2000 System</h3>
<ul>
<li><b>Múi 6° (EPSG:3405/3406)</b> — National-scale mapping. 2 zones.</li>
<li><b>Múi 3° (EPSG:9205–9218)</b> — Provincial cadastral. Each province has its own central meridian for maximum accuracy.</li>
</ul>

<p style='color:#888;font-size:10px'><i>Source: EPSG Registry, MONRE Vietnam</i></p>
</div>"""

    def _notes_vn(self):
        return """
<div style='font-family:Arial;font-size:12px;padding:8px'>
<h2 style='color:#1B5E20'>📖 Ghi chú CRS — Hiểu về Hệ tọa độ</h2>

<h3>🔹 CRS là gì?</h3>
<p><b>Hệ tọa độ tham chiếu (CRS)</b> xác định cách các con số tọa độ
ánh xạ tới vị trí thực trên Trái Đất. Không có CRS, dữ liệu chỉ là
các con số vô nghĩa về mặt địa lý.</p>

<h3>🔹 Set CRS vs. Reproject — Sự khác biệt quan trọng</h3>
<table border='1' cellpadding='6' style='border-collapse:collapse;width:100%'>
<tr style='background:#e3f2fd'><th width='30%'>Hành động</th><th>Xảy ra điều gì</th><th>Khi nào dùng</th></tr>
<tr><td><b>⚙️ Set CRS (Đặt CRS)</b></td>
<td>Chỉ <b>thay đổi nhãn</b>. Tọa độ giữ nguyên.
Giống dán nhãn mới lên hộp — ruột bên trong không đổi.</td>
<td>Dữ liệu đang bị gán NHẦM CRS (ví dụ: đơn vị mét nhưng gán thành độ).</td></tr>
<tr><td><b>🔄 Reproject (Chuyển đổi)</b></td>
<td><b>Tính toán lại mọi tọa độ</b> từ hệ này sang hệ khác.
Thay đổi thực sự giá trị X, Y.</td>
<td>Cần xuất dữ liệu sang CRS khác (ví dụ: VN-2000 → WGS 84).</td></tr>
</table>

<div style='background:#FFF3E0;padding:10px;border-left:4px solid #FF9800;margin:10px 0'>
<b>⚠️ Cảnh báo:</b> Nếu bạn dùng "Set CRS" thay vì "Reproject",
dữ liệu sẽ hiển thị SAI vị trí trên bản đồ!
</div>

<h3>🔹 Hệ tọa độ Địa lý vs. Phép chiếu</h3>
<table border='1' cellpadding='6' style='border-collapse:collapse;width:100%'>
<tr style='background:#E8F5E9'><th></th><th>Địa lý (EPSG:4326)</th><th>Phép chiếu (VN-2000, UTM)</th></tr>
<tr><td><b>Đơn vị</b></td><td>Độ (°)</td><td>Mét (m)</td></tr>
<tr><td><b>Tọa độ</b></td><td>Lat 16.05°, Lon 108.2°</td><td>X 583204, Y 1774521</td></tr>
<tr><td><b>Phù hợp</b></td><td>GPS, bản đồ web, toàn cầu</td><td>Tính diện tích/khoảng cách, địa chính</td></tr>
</table>

<h3>🔹 Hệ VN-2000</h3>
<ul>
<li><b>Múi 6° (EPSG:3405/3406)</b> — Bản đồ quy mô quốc gia. 2 múi.</li>
<li><b>Múi 3° (EPSG:9205–9218)</b> — Bản đồ địa chính cấp tỉnh. Mỗi tỉnh có kinh tuyến trục riêng để đạt độ chính xác cao nhất.</li>
</ul>

<p style='color:#888;font-size:10px'><i>Nguồn: EPSG Registry, Bộ TN&MT Việt Nam</i></p>
</div>"""
