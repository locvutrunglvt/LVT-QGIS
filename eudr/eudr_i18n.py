# -*- coding: utf-8 -*-
"""
LVT EUDR Module — Internationalization (i18n).

Bilingual translation system (English / Vietnamese) for the
EUDR GeoJSON Export panel.

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0

Reference:
    - EU Regulation 2023/1115 (EU Deforestation Regulation)
    - GeoJSON RFC 7946
"""

_EUDR_TRANSLATIONS = {
    # --- Window ---
    "EUDR GeoJSON Export": "Xuất GeoJSON EUDR",
    "EUDR GeoJSON Exporter — EU Regulation 2023/1115":
        "Công cụ Xuất GeoJSON EUDR — Quy định EU 2023/1115",

    # --- Language toggle ---
    "English": "English",
    "Vietnamese": "Tiếng Việt",

    # --- Group boxes ---
    "1. Select Layer": "1. Chọn Lớp dữ liệu",
    "2. EUDR Field Mapping": "2. Ánh xạ Trường EUDR",
    "3. Export Settings": "3. Cài đặt Xuất",
    "4. Validation & Statistics": "4. Kiểm tra & Thống kê",

    # --- Labels ---
    "Select Layer:": "Chọn lớp bản đồ:",
    "Geometry Type:": "Loại hình học:",
    "Feature Count:": "Số đối tượng:",
    "Layer CRS:": "Hệ tọa độ lớp:",
    "Output CRS:": "Hệ tọa độ đầu ra:",

    # --- EUDR Field labels ---
    "Production Place:": "Nơi sản xuất:",
    "Country of Production:": "Quốc gia sản xuất:",
    "Product Description:": "Mô tả sản phẩm:",
    "HS Code:": "Mã HS:",
    "Operator Name:": "Tên nhà vận hành:",
    "Plot ID:": "Mã lô:",
    "Area (ha):": "Diện tích (ha):",
    "Latitude:": "Vĩ độ:",
    "Longitude:": "Kinh độ:",
    "(auto — Point on Surface Y)": "(tự động — Điểm trên bề mặt Y)",
    "(auto — Point on Surface X)": "(tự động — Điểm trên bề mặt X)",
    "Date of Production:": "Ngày sản xuất:",

    # --- Field mapping hints ---
    "(select field or type value)": "(chọn trường hoặc nhập giá trị)",
    "(auto-calculated from geometry)": "(tự động tính từ hình học)",
    "(optional)": "(tùy chọn)",
    "(required for EUDR)": "(bắt buộc theo EUDR)",
    "-- Leave empty --": "-- Để trống --",
    "-- Manual value --": "-- Nhập thủ công --",

    # --- Export settings ---
    "Coordinate Precision (decimals):": "Độ chính xác tọa độ (số thập phân):",
    "Area Threshold (ha):": "Ngưỡng diện tích (ha):",
    "≤ threshold → Point centroid": "≤ ngưỡng → Điểm tâm",
    "> threshold → Polygon boundary": "> ngưỡng → Ranh giới đa giác",
    "Include area in properties": "Đưa diện tích vào thuộc tính",
    "Calculate area from geometry": "Tính diện tích từ hình học",
    "Use area field:": "Dùng trường diện tích:",
    "Validate geometries before export": "Kiểm tra hình học trước khi xuất",
    "Export Mode:": "Chế độ xuất:",

    # --- Statistics ---
    "Total features:": "Tổng số đối tượng:",
    "Point (≤ {threshold} ha):": "Điểm (≤ {threshold} ha):",
    "Polygon (> {threshold} ha):": "Đa giác (> {threshold} ha):",
    "Invalid geometries:": "Hình học không hợp lệ:",
    "Estimated file size:": "Kích thước tập tin dự kiến:",

    # --- Buttons ---
    "Refresh": "Làm mới",
    "Preview Statistics": "Xem thống kê",
    "Export GeoJSON": "Xuất GeoJSON",
    "Close": "Đóng",

    # --- Messages ---
    "Export completed successfully!\n\nFile: {path}\nFeatures: {count}\nPoints: {points}\nPolygons: {polygons}":
        "Xuất thành công!\n\nTập tin: {path}\nĐối tượng: {count}\nĐiểm: {points}\nĐa giác: {polygons}",
    "No vector layer selected.": "Chưa chọn lớp vector.",
    "Selected layer has no features.": "Lớp được chọn không có đối tượng.",
    "Export failed:\n{error}": "Xuất thất bại:\n{error}",
    "Please select a valid vector layer.": "Vui lòng chọn lớp vector hợp lệ.",
    "GeoJSON file size exceeds 25 MB limit. Consider splitting into multiple files.":
        "Tập tin GeoJSON vượt quá giới hạn 25 MB. Hãy chia thành nhiều tập tin.",
    "Found {count} invalid geometries. Fix before exporting.":
        "Phát hiện {count} hình học không hợp lệ. Hãy sửa trước khi xuất.",
    "All geometries are valid.": "Tất cả hình học đều hợp lệ.",
    "Save GeoJSON File": "Lưu tập tin GeoJSON",
    "GeoJSON Files (*.geojson)": "Tập tin GeoJSON (*.geojson)",
    "WGS84 (EPSG:4326) — Required by EUDR":
        "WGS84 (EPSG:4326) — Bắt buộc theo EUDR",

    # --- Tooltips ---
    "EUDR requires WGS84 (EPSG:4326) coordinates with ≥6 decimal precision.":
        "EUDR yêu cầu tọa độ WGS84 (EPSG:4326) với độ chính xác ≥6 số thập phân.",
    "Plots ≤ 4 ha: single point (centroid). Plots > 4 ha: polygon boundary.":
        "Lô ≤ 4 ha: điểm đơn (tâm). Lô > 4 ha: ranh giới đa giác.",
    "Map source layer fields to EUDR required properties.":
        "Ánh xạ trường dữ liệu nguồn sang thuộc tính bắt buộc EUDR.",

    # --- Guide tab ---
    "Guide": "Hướng dẫn",
    "Author": "Tác giả",

    # --- Validation messages ---
    "Polygon is not closed — auto-closing applied.":
        "Đa giác chưa đóng — đã tự động đóng.",
    "Self-intersecting polygon detected at feature {fid}. Attempting repair.":
        "Phát hiện đa giác tự cắt tại đối tượng {fid}. Đang thử sửa.",
    "Feature {fid} has null geometry — skipped.":
        "Đối tượng {fid} không có hình học — đã bỏ qua.",
    "CRS transformation applied: {src} → EPSG:4326":
        "Đã chuyển đổi hệ tọa độ: {src} → EPSG:4326",
}


def tr(text, lang=None):
    """Translate text based on language setting.

    Args:
        text: English text key.
        lang: 'en' or 'vi'. If None, uses shared language setting.

    Returns:
        str: Translated text or original if no translation found.
    """
    if lang is None:
        try:
            from ..shared.i18n import current_language
            lang = current_language()
        except (ImportError, ValueError):
            lang = 'vi'
    if lang == 'vi':
        return _EUDR_TRANSLATIONS.get(text, text)
    return text


def get_guide(lang='vi'):
    """Return the EUDR guide HTML for the Guide tab.

    Args:
        lang: 'en' or 'vi'.

    Returns:
        str: HTML content for the guide tab.
    """
    if lang == 'vi':
        return """
        <div style='font-family:Arial;padding:10px;'>
        <h2 style='color:#1B5E20;'>📘 Hướng dẫn Xuất GeoJSON EUDR</h2>
        <h3>Quy định EU 2023/1115 (EUDR) yêu cầu:</h3>
        <ul>
            <li><b>Hệ tọa độ:</b> WGS84 (EPSG:4326)</li>
            <li><b>Độ chính xác:</b> Tối thiểu 6 chữ số thập phân</li>
            <li><b>Lô ≤ 4 ha:</b> Có thể dùng 1 điểm (latitude/longitude)</li>
            <li><b>Lô > 4 ha:</b> Bắt buộc dùng đa giác (polygon)</li>
            <li><b>Đa giác:</b> Phải đóng kín, không tự cắt</li>
            <li><b>Kích thước file:</b> Tối đa 25 MB</li>
        </ul>

        <h3>Cách sử dụng:</h3>
        <ol>
            <li><b>Bước 1:</b> Chọn lớp vector chứa dữ liệu lô đất</li>
            <li><b>Bước 2:</b> Ánh xạ các trường dữ liệu sang trường EUDR</li>
            <li><b>Bước 3:</b> Kiểm tra thống kê (Point vs Polygon)</li>
            <li><b>Bước 4:</b> Nhấn "Xuất GeoJSON" để lưu file</li>
        </ol>

        <h3>Ánh xạ trường dữ liệu:</h3>
        <table border='1' cellpadding='5' style='border-collapse:collapse;width:100%;'>
            <tr style='background:#1B5E20;color:white;'>
                <th>Trường EUDR</th><th>Mô tả</th><th>Bắt buộc</th>
            </tr>
            <tr><td>ProductionPlace</td><td>Tên nơi sản xuất</td><td>Có</td></tr>
            <tr><td>Country</td><td>Quốc gia sản xuất (mã ISO)</td><td>Có</td></tr>
            <tr><td>ProductDescription</td><td>Mô tả sản phẩm</td><td>Không</td></tr>
            <tr><td>HSCode</td><td>Mã HS (Harmonized System)</td><td>Không</td></tr>
            <tr><td>OperatorName</td><td>Tên nhà vận hành/doanh nghiệp</td><td>Không</td></tr>
            <tr><td>PlotID</td><td>Mã lô đất</td><td>Có</td></tr>
            <tr><td>Area_ha</td><td>Diện tích (hecta)</td><td>Có</td></tr>
            <tr><td>ProductionDate</td><td>Ngày sản xuất</td><td>Không</td></tr>
        </table>

        <h3>Lưu ý quan trọng:</h3>
        <ul>
            <li>Hệ thống tự động chuyển đổi CRS về WGS84</li>
            <li>Đa giác tự động được kiểm tra và sửa lỗi (đóng kín, tự cắt)</li>
            <li>Diện tích có thể tự tính từ geometry hoặc lấy từ trường dữ liệu</li>
        </ul>
        </div>
        """
    else:
        return """
        <div style='font-family:Arial;padding:10px;'>
        <h2 style='color:#1B5E20;'>📘 EUDR GeoJSON Export Guide</h2>
        <h3>EU Regulation 2023/1115 (EUDR) Requirements:</h3>
        <ul>
            <li><b>CRS:</b> WGS84 (EPSG:4326)</li>
            <li><b>Precision:</b> Minimum 6 decimal digits</li>
            <li><b>Plots ≤ 4 ha:</b> Single point (lat/lon) acceptable</li>
            <li><b>Plots > 4 ha:</b> Polygon boundary mandatory</li>
            <li><b>Polygons:</b> Must be closed, non-self-intersecting</li>
            <li><b>File size:</b> Maximum 25 MB</li>
        </ul>

        <h3>How to use:</h3>
        <ol>
            <li><b>Step 1:</b> Select vector layer with plot data</li>
            <li><b>Step 2:</b> Map source fields to EUDR properties</li>
            <li><b>Step 3:</b> Review statistics (Point vs Polygon)</li>
            <li><b>Step 4:</b> Click "Export GeoJSON" to save</li>
        </ol>

        <h3>Field Mapping:</h3>
        <table border='1' cellpadding='5' style='border-collapse:collapse;width:100%;'>
            <tr style='background:#1B5E20;color:white;'>
                <th>EUDR Field</th><th>Description</th><th>Required</th>
            </tr>
            <tr><td>ProductionPlace</td><td>Production location name</td><td>Yes</td></tr>
            <tr><td>Country</td><td>Country of production (ISO code)</td><td>Yes</td></tr>
            <tr><td>ProductDescription</td><td>Product description</td><td>No</td></tr>
            <tr><td>HSCode</td><td>Harmonized System code</td><td>No</td></tr>
            <tr><td>OperatorName</td><td>Operator/company name</td><td>No</td></tr>
            <tr><td>PlotID</td><td>Plot identifier</td><td>Yes</td></tr>
            <tr><td>Area_ha</td><td>Area in hectares</td><td>Yes</td></tr>
            <tr><td>ProductionDate</td><td>Date of production</td><td>No</td></tr>
        </table>

        <h3>Important Notes:</h3>
        <ul>
            <li>CRS is automatically transformed to WGS84</li>
            <li>Polygons are validated and repaired (closure, self-intersection)</li>
            <li>Area can be auto-calculated from geometry or taken from a field</li>
        </ul>
        </div>
        """
