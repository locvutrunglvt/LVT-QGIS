# -*- coding: utf-8 -*-
"""
LVT Font Converter — Convert font encoding for a vector layer and export.

Supports:
  - TCVN3 (ABC) → Unicode
  - VNI → Unicode
  - No conversion (just re-export with format/CRS change)
  - Export to SHP (with .cpg for MapInfo) or MapInfo TAB

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""
import os
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QFormLayout, QCheckBox,
    QMessageBox, QFileDialog, QTextEdit, QProgressBar,
    QApplication,
)
from qgis.core import (
    QgsProject, QgsCoordinateReferenceSystem, QgsVectorLayer,
    QgsVectorFileWriter, QgsCoordinateTransformContext,
    QgsCoordinateTransform,
    QgsField, QgsFeature, QgsFields, QgsWkbTypes,
)
from qgis.gui import QgsMapLayerComboBox

from ..shared.i18n import current_language

# ═══════════════════════════════════════════════════════════════
# TCVN3 → Unicode mapping (byte-level, comprehensive)
# ═══════════════════════════════════════════════════════════════
_TCVN3_TO_UNICODE = {
    # Lowercase - ă group
    '\xb0': 'ă', '\xb1': 'ắ', '\xb2': 'ằ', '\xb3': 'ẳ', '\xb4': 'ẵ', '\xb5': 'ặ',
    # â group
    '\xa9': 'â', '\xca': 'ấ', '\xa7': 'ầ', '\xa8': 'ẩ', '\xc9': 'ẫ', '\xcb': 'ậ',
    # ê group
    '\xaa': 'ê', '\xd5': 'ế', '\xd2': 'ề', '\xd3': 'ể', '\xd4': 'ễ', '\xd6': 'ệ',
    # ô group
    '\xab': 'ô', '\xe8': 'ố', '\xe5': 'ồ', '\xe6': 'ổ', '\xe7': 'ỗ', '\xe9': 'ộ',
    # ơ group
    '\xac': 'ơ', '\xed': 'ớ', '\xea': 'ờ', '\xeb': 'ở', '\xec': 'ỡ', '\xee': 'ợ',
    # ư group
    '\xad': 'ư', '\xf8': 'ứ', '\xf5': 'ừ', '\xf6': 'ử', '\xf7': 'ữ', '\xf9': 'ự',
    # đ
    '\xae': 'đ',
    # Standalone tones: a e i o u y
    '\xe1': 'á', '\xe0': 'à', '\xe2': 'ả', '\xe3': 'ã', '\xe4': 'ạ',
    '\xd0': 'é', '\xcf': 'è', '\xd1': 'ẻ', '\xce': 'ẽ', '\xd7': 'ẹ',
    '\xdd': 'í', '\xd8': 'ì', '\xd9': 'ỉ', '\xdc': 'ĩ', '\xde': 'ị',
    '\xf3': 'ó', '\xef': 'ò', '\xf0': 'ỏ', '\xf2': 'õ', '\xf4': 'ọ',
    '\xfa': 'ú', '\xf1': 'ù', '\xfb': 'ủ', '\xfc': 'ũ', '\xfe': 'ụ',
    '\xfd': 'ý', '\xdf': 'ỳ', '\xdb': 'ỷ', '\xda': 'ỹ', '\xff': 'ỵ',
    # Uppercase
    '\x80': 'Ă', '\x81': 'Ắ', '\x82': 'Ằ', '\x83': 'Ẳ', '\x84': 'Ẵ', '\x85': 'Ặ',
    '\x86': 'Â', '\x87': 'Ấ', '\x88': 'Ầ', '\x89': 'Ẩ', '\x8a': 'Ẫ', '\x8b': 'Ậ',
    '\x8c': 'Ê', '\x8d': 'Ế', '\x8e': 'Ề', '\x8f': 'Ể', '\x90': 'Ễ', '\x91': 'Ệ',
    '\x92': 'Ô', '\x93': 'Ố', '\x94': 'Ồ', '\x95': 'Ổ', '\x96': 'Ỗ', '\x97': 'Ộ',
    '\x9e': 'Ơ', '\x9a': 'Ớ', '\x9b': 'Ờ', '\x9c': 'Ở', '\x9d': 'Ỡ', '\x9f': 'Ợ',
    '\xa0': 'Ư', '\xa1': 'Ứ', '\xa2': 'Ừ', '\xa3': 'Ử', '\xa4': 'Ữ', '\xa5': 'Ự',
    '\xa6': 'Đ',
    '\xc1': 'Á', '\xc0': 'À', '\xc2': 'Ả', '\xc3': 'Ã', '\xc4': 'Ạ',
    '\xc5': 'É', '\xc6': 'È', '\xc7': 'Ẻ', '\xc8': 'Ẽ', '\x98': 'Ẹ',
    '\xcc': 'Í', '\x99': 'Ì', '\xcd': 'Ỉ',
}

# Build reverse: Unicode char → TCVN3 code point (for .VnTime font)
_UNICODE_TO_TCVN3 = {v: k for k, v in _TCVN3_TO_UNICODE.items()}

# ═══════════════════════════════════════════════════════════════
# VNI → Unicode mapping
# ═══════════════════════════════════════════════════════════════
_VNI_TO_UNICODE = {
    'aê': 'ă', 'AÊ': 'Ă',
    'aé': 'ắ', 'Aé': 'Ắ', 'aè': 'ằ', 'Aè': 'Ằ',
    'aú': 'ẳ', 'Aú': 'Ẳ', 'aû': 'ẵ', 'Aû': 'Ẵ', 'aë': 'ặ', 'Aë': 'Ặ',
    'aâ': 'â', 'AÂ': 'Â',
    'aá': 'ấ', 'Aá': 'Ấ', 'aà': 'ầ', 'Aà': 'Ầ',
    'aå': 'ẩ', 'Aå': 'Ẩ', 'aã': 'ẫ', 'Aã': 'Ẫ', 'aä': 'ậ', 'Aä': 'Ậ',
    'eâ': 'ê', 'EÂ': 'Ê',
    'eá': 'ế', 'Eá': 'Ế', 'eà': 'ề', 'Eà': 'Ề',
    'eå': 'ể', 'Eå': 'Ể', 'eã': 'ễ', 'Eã': 'Ễ', 'eä': 'ệ', 'Eä': 'Ệ',
    'oâ': 'ô', 'OÂ': 'Ô',
    'oá': 'ố', 'Oá': 'Ố', 'oà': 'ồ', 'Oà': 'Ồ',
    'oå': 'ổ', 'Oå': 'Ổ', 'oã': 'ỗ', 'Oã': 'Ỗ', 'oä': 'ộ', 'Oä': 'Ộ',
    'ôù': 'ớ', 'ôø': 'ờ', 'ôû': 'ở', 'ôõ': 'ỡ', 'ôï': 'ợ',
    'öù': 'ứ', 'öø': 'ừ', 'öû': 'ử', 'öõ': 'ữ', 'öï': 'ự',
    'ô': 'ơ', 'Ô': 'Ơ', 'ö': 'ư', 'Ö': 'Ư',
    'ñ': 'đ', 'Ñ': 'Đ',
    'aù': 'á', 'aø': 'à', 'aõ': 'ã', 'aï': 'ạ',
    'eù': 'é', 'eø': 'è', 'eû': 'ẻ', 'eõ': 'ẽ', 'eï': 'ẹ',
    'où': 'ó', 'oø': 'ò', 'oû': 'ỏ', 'oõ': 'õ', 'oï': 'ọ',
    'uù': 'ú', 'uø': 'ù', 'uû': 'ủ', 'uõ': 'ũ', 'uï': 'ụ',
    'yù': 'ý', 'yø': 'ỳ', 'yû': 'ỷ', 'yõ': 'ỹ',
}

# CRS list (shared across modules)
from .._crs_list import CRS_LIST


class FontConverterDialog(QDialog):
    """Font Converter: change encoding + export SHP/TAB with CRS."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("LVT — Font Converter / Chuyển đổi Font")
        self.setMinimumSize(580, 460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        ly = QVBoxLayout(self)

        # Header
        hdr = QLabel("<h3>🔤 Font Converter / Chuyển đổi Font chữ</h3>")
        ly.addWidget(hdr)
        ly.addWidget(QLabel(
            "Chuyển font TCVN3/VNI → Unicode, xuất Shapefile hoặc MapInfo TAB."
        ))

        form = QFormLayout()

        # Layer
        self.cmb_layer = QgsMapLayerComboBox()
        form.addRow("Layer:", self.cmb_layer)

        # Conversion mode
        self.cmb_from = QComboBox()
        self.cmb_from.addItems([
            "TCVN3 (ABC) → Unicode",
            "VNI → Unicode",
            "Unicode → TCVN3 (.VnTime)",
            "Không chuyển font / No conversion",
        ])
        form.addRow("Chuyển đổi / Convert:", self.cmb_from)

        # Output format
        self.cmb_format = QComboBox()
        self.cmb_format.addItems([
            "📁 Shapefile (*.shp)",
            "📁 MapInfo TAB (*.tab)",
        ])
        form.addRow("Định dạng / Format:", self.cmb_format)

        # Target CRS
        self.cmb_crs = QComboBox()
        for label, _ in CRS_LIST:
            self.cmb_crs.addItem(label)
        for i, (_, code) in enumerate(CRS_LIST):
            if not code:
                self.cmb_crs.model().item(i).setEnabled(False)
        form.addRow("CRS xuất / Export CRS:", self.cmb_crs)

        ly.addLayout(form)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        ly.addWidget(self.progress)

        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        self.log.setVisible(False)
        ly.addWidget(self.log)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_convert = QPushButton("🔄 Convert & Export / Chuyển đổi & Xuất")
        self.btn_convert.setStyleSheet(
            "QPushButton{background:#2e7d32;color:#fff;font-weight:bold;"
            "padding:8px 20px;border-radius:4px}"
            "QPushButton:hover{background:#388e3c}"
        )
        self.btn_convert.clicked.connect(self._do_convert)
        btn_row.addWidget(self.btn_convert)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        ly.addLayout(btn_row)
        ly.addStretch()

    def refresh_layers(self):
        pass  # QgsMapLayerComboBox auto-refreshes

    # ═══════════════════════════════════════════════════════════════
    # Main export logic
    # ═══════════════════════════════════════════════════════════════
    def _do_convert(self):
        layer = self.cmb_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, "LVT", "No layer selected.")
            return

        # --- CRS ---
        idx = self.cmb_crs.currentIndex()
        crs_code = CRS_LIST[idx][1]
        if not crs_code:
            crs_code = layer.crs().authid()
        target_crs = QgsCoordinateReferenceSystem(crs_code)
        if not target_crs.isValid():
            target_crs = layer.crs()

        # --- Mode ---
        mode = self.cmb_from.currentIndex()  # 0=TCVN3→Uni, 1=VNI→Uni, 2=Uni→TCVN3, 3=none

        # --- Format ---
        fmt_idx = self.cmb_format.currentIndex()  # 0=SHP, 1=TAB
        if fmt_idx == 1:
            filt = "MapInfo TAB (*.tab)"
            driver = "MapInfo File"
            ext = ".tab"
        else:
            filt = "Shapefile (*.shp)"
            driver = "ESRI Shapefile"
            ext = ".shp"

        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", filt)
        if not path:
            return
        if not path.lower().endswith(ext):
            path += ext

        self.progress.setVisible(True)
        self.log.setVisible(True)
        self.log.clear()
        self.btn_convert.setEnabled(False)
        QApplication.processEvents()

        try:
            self._export(layer, path, driver, ext, mode, target_crs)
        except Exception as e:
            self.log.append(f"❌ Exception: {e}")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.btn_convert.setEnabled(True)
            self.progress.setVisible(False)

    def _export(self, layer, path, driver, ext, mode, target_crs):
        """Build a memory layer with converted text, then write to disk."""
        features = list(layer.getFeatures())
        total = len(features)
        self.progress.setMaximum(total + 10)
        self.progress.setValue(0)

        fields = layer.fields()
        text_field_indices = [
            i for i in range(fields.count())
            if fields.field(i).typeName().lower() in ('string', 'text', 'varchar')
        ]

        mode_labels = ["TCVN3 → Unicode", "VNI → Unicode", "Unicode → TCVN3", "No conversion"]
        self.log.append(f"📋 Layer: {layer.name()} — {total} features")
        self.log.append(f"🔤 Text fields: {len(text_field_indices)}")
        self.log.append(f"🔄 Mode: {mode_labels[mode]}")
        self.log.append(f"💾 Format: {driver}")
        QApplication.processEvents()

        # --- Step 1: Convert text in memory ---
        converted_count = 0
        new_features = []
        for i, feat in enumerate(features):
            self.progress.setValue(i + 1)
            new_feat = QgsFeature(fields)
            new_feat.setGeometry(feat.geometry())
            attrs = list(feat.attributes())
            for fi in text_field_indices:
                val = attrs[fi]
                if isinstance(val, str) and val:
                    if mode == 0:
                        new_val = self._convert_tcvn3_to_unicode(val)
                    elif mode == 1:
                        new_val = self._convert_vni_to_unicode(val)
                    elif mode == 2:
                        new_val = self._convert_unicode_to_tcvn3(val)
                    else:
                        new_val = val
                    if new_val != val:
                        converted_count += 1
                    attrs[fi] = new_val
            new_feat.setAttributes(attrs)
            new_features.append(new_feat)

        self.log.append(f"🔤 Converted: {converted_count} values")
        self.progress.setValue(total + 2)
        QApplication.processEvents()

        # --- Step 2: Create memory layer ---
        geom_type = QgsWkbTypes.displayString(layer.wkbType())
        mem_uri = f"{geom_type}?crs={layer.crs().authid()}"
        mem = QgsVectorLayer(mem_uri, "converted", "memory")
        prov = mem.dataProvider()
        prov.addAttributes(fields.toList())
        mem.updateFields()
        prov.addFeatures(new_features)

        self.progress.setValue(total + 5)
        QApplication.processEvents()

        # --- Step 3: Write to disk (always UTF-8) ---
        self.log.append(f"💾 Writing → {os.path.basename(path)}")
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = driver
        options.fileEncoding = "UTF-8"

        # Handle CRS transform
        need_reproj = (layer.crs() != target_crs)
        if need_reproj:
            options.ct = QgsCoordinateTransform(
                layer.crs(), target_crs, QgsProject.instance()
            )
            self.log.append(f"🌐 Reprojecting: {layer.crs().authid()} → {target_crs.authid()}")

        ctx = QgsCoordinateTransformContext()
        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            mem, path, ctx, options
        )

        self.progress.setValue(total + 8)
        QApplication.processEvents()

        if error[0] != QgsVectorFileWriter.NoError:
            self.log.append(f"❌ Write error: {error}")
            QMessageBox.critical(self, "Error", str(error))
            return

        # --- Step 4: Write .cpg file for SHP (tells MapInfo encoding) ---
        if driver == "ESRI Shapefile":
            cpg_path = path.replace(".shp", ".cpg").replace(".SHP", ".cpg")
            try:
                with open(cpg_path, 'w') as f:
                    f.write("UTF-8")
                self.log.append(f"📄 Created {os.path.basename(cpg_path)} (UTF-8)")
            except Exception as e:
                self.log.append(f"⚠️ Could not write .cpg: {e}")

        # --- Step 5: Add result to project ---
        result_layer = QgsVectorLayer(
            path, os.path.basename(path).replace(ext, ''), "ogr"
        )
        if result_layer.isValid():
            QgsProject.instance().addMapLayer(result_layer)
            self.log.append(f"✅ Added to project: {result_layer.name()}")

        self.progress.setValue(total + 10)

        crs_str = target_crs.authid() if need_reproj else layer.crs().authid()
        self.log.append(
            f"\n✅ HOÀN THÀNH!\n"
            f"   File: {os.path.basename(path)}\n"
            f"   CRS: {crs_str}\n"
            f"   Features: {total}\n"
            f"   Font conversions: {converted_count}\n"
            f"   Encoding: UTF-8"
        )

        tip = ""
        if driver == "ESRI Shapefile":
            tip = (
                "\n💡 Mở trong MapInfo:\n"
                "   File > Open > chọn SHP > Encoding: UTF-8\n"
                "   Sau đó Table > Export > MapInfo TAB"
            )
        elif driver == "MapInfo File":
            tip = (
                "\n💡 File TAB đã ghi với charset UTF-8.\n"
                "   MapInfo Pro sẽ đọc đúng tiếng Việt Unicode."
            )

        QMessageBox.information(
            self, "✅ Done / Hoàn thành",
            f"Exported {total} features → {os.path.basename(path)}\n"
            f"Format: {driver}\n"
            f"CRS: {crs_str}\n"
            f"Font conversions: {converted_count}\n"
            f"Encoding: UTF-8"
            + tip
        )

    # ═══════════════════════════════════════════════════════════════
    # Conversion engines
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def _convert_tcvn3_to_unicode(text):
        """Convert TCVN3 (ABC) encoded text to Unicode, char by char."""
        return ''.join(_TCVN3_TO_UNICODE.get(ch, ch) for ch in text)

    @staticmethod
    def _convert_unicode_to_tcvn3(text):
        """Convert Unicode Vietnamese to TCVN3 code points (.VnTime font)."""
        return ''.join(_UNICODE_TO_TCVN3.get(ch, ch) for ch in text)

    @staticmethod
    def _convert_vni_to_unicode(text):
        """Convert VNI encoded text to Unicode."""
        result = text
        for old, new in sorted(_VNI_TO_UNICODE.items(), key=lambda x: -len(x[0])):
            result = result.replace(old, new)
        return result
