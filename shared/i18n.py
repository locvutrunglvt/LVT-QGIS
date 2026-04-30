# -*- coding: utf-8 -*-
"""
LVT Shared Infrastructure — Internationalization (i18n).

Bilingual translation system (English / Vietnamese) with persistent
language preference stored via QSettings.

The translation dictionary covers all menu items, messages, and UI labels
used across the LVT Plugin Suite.

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""

from qgis.PyQt.QtCore import QSettings

# QSettings key for persisting the language choice
_SETTINGS_KEY = "LVT4U/language"

# Default language
_DEFAULT_LANG = "en"

# Translation dictionary: English key → Vietnamese translation
# English is the base language (key = display text)
_TRANSLATIONS = {
    # --- Menu items ---
    "Map Layout": "Xây dựng Layout bản đồ",
    "KML": "KML",
    "SHP → KML/KMZ": "SHP → KML/KMZ",
    "KML/KMZ → SHP": "KML/KMZ → SHP",
    "Create MBTiles": "Tạo MBTiles",
    "Create GeoJSON EUDR": "Tạo GeoJSON EUDR",
    "EUDR": "EUDR",
    "Export GeoJSON": "Xuất GeoJSON",
    "Reference Documents": "Tài liệu tham khảo",
    "Package Map": "Đóng gói bản đồ",
    "Thematic Map": "Bản đồ chuyên đề",
    "Circular 16/2023": "Theo TT 16/2023",
    "Plot Labels": "Nhãn lô",
    "Basemap": "Bản đồ nền",
    "Google Maps": "Google Maps",
    "Google Satellite": "Google Satellite",
    "Google Hybrid": "Google Hybrid",
    "Legal Documents": "Văn bản pháp lý",
    "Font Converter": "Chuyển đổi font chữ",
    "Coordinate System": "Hệ tọa độ",
    "CRS Conversion": "Chuyển đổi hệ tọa độ",
    "Define CRS": "Định nghĩa hệ tọa độ",
    "CRS Catalog": "Danh mục hệ tọa độ",
    "About": "Thông tin",

    # --- Messages ---
    "{module} — Coming soon!": "{module} — Sắp ra mắt!",
    "{name} added successfully.": "{name} đã được thêm thành công.",
    "{name} is already loaded.": "{name} đã được tải rồi.",
    "Failed to load {name}.": "Không thể tải {name}.",

    # --- About dialog ---
    "Author": "Tác giả",
    "Version": "Phiên bản",
    "License": "Giấy phép",
    "Language": "Ngôn ngữ",
    "English": "English",
    "Vietnamese": "Tiếng Việt",
    "Close": "Đóng",
    "Settings saved. Restart QGIS to apply.": "Đã lưu. Khởi động lại QGIS để áp dụng.",

    # --- Common ---
    "OK": "OK",
    "Cancel": "Hủy",
    "Apply": "Áp dụng",
    "Browse...": "Chọn...",
    "Output folder": "Thư mục đầu ra",
    "Input layer": "Layer đầu vào",
    "Output file": "File đầu ra",
    "Select": "Chọn",
    "Error": "Lỗi",
    "Warning": "Cảnh báo",
    "Success": "Thành công",
    "Processing...": "Đang xử lý...",
}


def current_language():
    """Return the currently selected language code.

    Returns:
        str: "en" or "vi".
    """
    return QSettings().value(_SETTINGS_KEY, _DEFAULT_LANG)


def set_language(lang_code):
    """Persist the language preference.

    Args:
        lang_code: "en" for English, "vi" for Vietnamese.
    """
    if lang_code in ("en", "vi"):
        QSettings().setValue(_SETTINGS_KEY, lang_code)


def tr(text):
    """Translate the given text based on the current language setting.

    If the current language is English, the original text is returned.
    If Vietnamese is selected, the translation is looked up in the dictionary.
    If no translation is found, the original English text is returned as fallback.

    Args:
        text: English text to translate.

    Returns:
        str: Translated text (or original if no translation available).
    """
    if current_language() == "vi":
        return _TRANSLATIONS.get(text, text)
    return text
