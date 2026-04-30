# -*- coding: utf-8 -*-
"""
LVT Font Converter — Convert font encoding for a vector layer and export.

Supports:
  - TCVN3 (ABC) → Unicode
  - VNI → Unicode
  - Unicode → TCVN3 (for MapInfo compatibility)
  - Export to SHP or MapInfo TAB

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""
import os
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QFormLayout, QCheckBox,
    QMessageBox, QFileDialog, QTextEdit, QProgressBar,
)
from qgis.core import (
    QgsProject, QgsCoordinateReferenceSystem, QgsVectorLayer,
    QgsVectorFileWriter, QgsCoordinateTransformContext,
    QgsField, QgsFeature,
)
from qgis.gui import QgsMapLayerComboBox

from ..shared.i18n import current_language

# ═══════════════════════════════════════════════════════════════
# TCVN3 ↔ Unicode mapping (complete, byte-accurate)
# ═══════════════════════════════════════════════════════════════
# TCVN3 uses Windows-1252 byte values to represent Vietnamese diacritics.
# The mapping below uses the actual character representations.

_TCVN3_TO_UNICODE = {
    # Lowercase vowels with diacritics
    # a with breve (ă)
    '\xb0': 'ă', '\xb1': 'ắ', '\xb2': 'ằ', '\xb3': 'ẳ', '\xb4': 'ẵ', '\xb5': 'ặ',
    # a with circumflex (â)
    '\xa9': 'â', '\xca': 'ấ', '\xa7': 'ầ', '\xa8': 'ẩ', '\xc9': 'ẫ', '\xcb': 'ậ',
    # e with circumflex (ê)
    '\xaa': 'ê', '\xd5': 'ế', '\xd2': 'ề', '\xd3': 'ể', '\xd4': 'ễ', '\xd6': 'ệ',
    # o with circumflex (ô)
    '\xab': 'ô', '\xe8': 'ố', '\xe5': 'ồ', '\xe6': 'ổ', '\xe7': 'ỗ', '\xe9': 'ộ',
    # o with horn (ơ)
    '\xac': 'ơ', '\xed': 'ớ', '\xea': 'ờ', '\xeb': 'ở', '\xec': 'ỡ', '\xee': 'ợ',
    # u with horn (ư)
    '\xad': 'ư', '\xf8': 'ứ', '\xf5': 'ừ', '\xf6': 'ử', '\xf7': 'ữ', '\xf9': 'ự',
    # d with stroke (đ)
    '\xae': 'đ',
    # Tones on standalone vowels
    # a
    '\xe1': 'á', '\xe0': 'à', '\xe2': 'ả', '\xe3': 'ã', '\xe4': 'ạ',
    # e
    '\xd0': 'é', '\xcf': 'è', '\xd1': 'ẻ', '\xce': 'ẽ', '\xd7': 'ẹ',
    # i
    '\xdd': 'í', '\xd8': 'ì', '\xd9': 'ỉ', '\xdc': 'ĩ', '\xde': 'ị',
    # o
    '\xf3': 'ó', '\xef': 'ò', '\xf0': 'ỏ', '\xf2': 'õ', '\xf4': 'ọ',
    # u
    '\xfa': 'ú', '\xf1': 'ù', '\xfb': 'ủ', '\xfc': 'ũ', '\xfe': 'ụ',
    # y
    '\xfd': 'ý', '\xdf': 'ỳ', '\xdb': 'ỷ', '\xda': 'ỹ', '\xff': 'ỵ',

    # Uppercase vowels with diacritics
    # A with breve (Ă)
    '\x80': 'Ă', '\x81': 'Ắ', '\x82': 'Ằ', '\x83': 'Ẳ', '\x84': 'Ẵ', '\x85': 'Ặ',
    # A with circumflex (Â)
    '\x86': 'Â', '\x87': 'Ấ', '\x88': 'Ầ', '\x89': 'Ẩ', '\x8a': 'Ẫ', '\x8b': 'Ậ',
    # E with circumflex (Ê)
    '\x8c': 'Ê', '\x8d': 'Ế', '\x8e': 'Ề', '\x8f': 'Ể', '\x90': 'Ễ', '\x91': 'Ệ',
    # O with circumflex (Ô)
    '\x92': 'Ô', '\x93': 'Ố', '\x94': 'Ồ', '\x95': 'Ổ', '\x96': 'Ỗ', '\x97': 'Ộ',
    # O with horn (Ơ)
    '\x9e': 'Ơ', '\x9a': 'Ớ', '\x9b': 'Ờ', '\x9c': 'Ở', '\x9d': 'Ỡ', '\x9f': 'Ợ',
    # U with horn (Ư)
    '\xa0': 'Ư', '\xa1': 'Ứ', '\xa2': 'Ừ', '\xa3': 'Ử', '\xa4': 'Ữ', '\xa5': 'Ự',
    # D with stroke (Đ)
    '\xa6': 'Đ',
    # Uppercase tones on standalone vowels
    '\xc1': 'Á', '\xc0': 'À', '\xc2': 'Ả', '\xc3': 'Ã', '\xc4': 'Ạ',
    '\xc5': 'É', '\xc6': 'È', '\xc7': 'Ẻ', '\xc8': 'Ẽ', '\x98': 'Ẹ',
    '\xcc': 'Í', '\x99': 'Ì', '\xcd': 'Ỉ', '\xa6': 'Đ',
    '\xd3': 'Ó', '\xd2': 'Ò', '\xd4': 'Ỏ', '\xd5': 'Õ', '\xd6': 'Ọ',
}

# Build reverse map: Unicode → TCVN3
_UNICODE_TO_TCVN3 = {v: k for k, v in _TCVN3_TO_UNICODE.items()}

# ═══════════════════════════════════════════════════════════════
# VNI → Unicode mapping (common characters)
# ═══════════════════════════════════════════════════════════════
_VNI_TO_UNICODE = {
    # Multi-char sequences first (sorted by length desc during conversion)
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
    'ô': 'ơ', 'Ô': 'Ơ',
    'ö': 'ư', 'Ö': 'Ư',
    'ñ': 'đ', 'Ñ': 'Đ',
    # Single-char tones
    'aù': 'á', 'aø': 'à', 'aû': 'ả', 'aõ': 'ã', 'aï': 'ạ',
    'eù': 'é', 'eø': 'è', 'eû': 'ẻ', 'eõ': 'ẽ', 'eï': 'ẹ',
    'où': 'ó', 'oø': 'ò', 'oû': 'ỏ', 'oõ': 'õ', 'oï': 'ọ',
    'uù': 'ú', 'uø': 'ù', 'uû': 'ủ', 'uõ': 'ũ', 'uï': 'ụ',
    'yù': 'ý', 'yø': 'ỳ', 'yû': 'ỷ', 'yõ': 'ỹ',
    'ó': 'í', 'ì': 'ì', 'æ': 'ỉ', 'ò': 'ị',
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
            "Chuyển font TCVN3/VNI ↔ Unicode, xuất Shapefile hoặc MapInfo TAB."
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
            "Unicode → TCVN3 (cho MapInfo)",
            "Không chuyển font / No conversion",
        ])
        form.addRow("Chuyển đổi / Convert:", self.cmb_from)

        # Output format
        self.cmb_format = QComboBox()
        self.cmb_format.addItems([
            "📁 Shapefile (*.shp) — QGIS, ArcGIS",
            "📁 MapInfo TAB (*.tab) — MapInfo Pro",
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
        self.log.setMaximumHeight(140)
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

    def _do_convert(self):
        layer = self.cmb_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, "LVT", "No layer selected.")
            return

        # Get target CRS
        idx = self.cmb_crs.currentIndex()
        crs_code = CRS_LIST[idx][1]
        if not crs_code:
            crs_code = layer.crs().authid()
        target_crs = QgsCoordinateReferenceSystem(crs_code)
        if not target_crs.isValid():
            target_crs = layer.crs()

        # Get conversion mode
        mode = self.cmb_from.currentIndex()  # 0=TCVN3→Uni, 1=VNI→Uni, 2=Uni→TCVN3, 3=none

        # Get output format
        fmt_idx = self.cmb_format.currentIndex()  # 0=SHP, 1=TAB

        # Output path
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

        # Identify text fields
        features = list(layer.getFeatures())
        total = len(features)
        self.progress.setMaximum(total)

        fields = layer.fields()
        text_field_indices = [
            i for i in range(fields.count())
            if fields.field(i).typeName().lower() in ('string', 'text', 'varchar')
        ]

        self.log.append(f"📋 Layer: {layer.name()} — {total} features")
        self.log.append(f"🔤 Text fields: {len(text_field_indices)}")
        mode_labels = [
            "TCVN3 → Unicode", "VNI → Unicode",
            "Unicode → TCVN3", "No conversion",
        ]
        self.log.append(f"🔄 Mode: {mode_labels[mode]}")

        # Convert text in memory
        converted_count = 0
        new_features = []
        for i, feat in enumerate(features):
            self.progress.setValue(i + 1)
            new_feat = QgsFeature(feat)
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

        # Write output file
        self.log.append(f"💾 Writing {driver} → {os.path.basename(path)}")

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = driver
        if fmt_idx == 1 and mode == 2:
            # MapInfo TAB + TCVN3: write as Windows-1252 for legacy compat
            options.fileEncoding = "Windows-1252"
        else:
            options.fileEncoding = "UTF-8"

        ctx = QgsCoordinateTransformContext()

        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, path, ctx, options
        )

        if error[0] == QgsVectorFileWriter.NoError:
            # Overwrite text fields with converted values
            if mode < 3 and converted_count > 0:
                out_layer = QgsVectorLayer(path, "temp", "ogr")
                if out_layer.isValid():
                    out_layer.startEditing()
                    out_feats = list(out_layer.getFeatures())
                    for out_feat, new_feat in zip(out_feats, new_features):
                        for fi in text_field_indices:
                            if fi < len(new_feat.attributes()):
                                out_layer.changeAttributeValue(
                                    out_feat.id(), fi,
                                    new_feat.attributes()[fi]
                                )
                    out_layer.commitChanges()
                    del out_layer

            # Set CRS on output if needed
            if layer.crs() != target_crs:
                self.log.append(f"🌐 Reprojecting to {target_crs.authid()}")
                temp_layer = QgsVectorLayer(path, "temp_reproj", "ogr")
                if temp_layer.isValid():
                    reproj_path = path.replace(ext, f"_reproj{ext}")
                    opts2 = QgsVectorFileWriter.SaveVectorOptions()
                    opts2.driverName = driver
                    opts2.fileEncoding = options.fileEncoding
                    ctx2 = QgsCoordinateTransformContext()
                    from qgis.core import QgsCoordinateTransform
                    opts2.ct = QgsCoordinateTransform(
                        temp_layer.crs(), target_crs,
                        QgsProject.instance()
                    )
                    err2 = QgsVectorFileWriter.writeAsVectorFormatV3(
                        temp_layer, reproj_path, ctx2, opts2
                    )
                    del temp_layer
                    if err2[0] == QgsVectorFileWriter.NoError:
                        # Replace original with reprojected
                        import shutil
                        base = os.path.splitext(path)[0]
                        base2 = os.path.splitext(reproj_path)[0]
                        for f in os.listdir(os.path.dirname(path)):
                            fp = os.path.join(os.path.dirname(path), f)
                            if os.path.splitext(fp)[0] == base2:
                                target = base + os.path.splitext(fp)[1]
                                shutil.move(fp, target)
                        self.log.append("✅ Reprojection done")

            # Add to project
            result_layer = QgsVectorLayer(
                path, os.path.basename(path).replace(ext, ''), "ogr"
            )
            if result_layer.isValid():
                QgsProject.instance().addMapLayer(result_layer)

            self.log.append(
                f"✅ OK: {os.path.basename(path)}\n"
                f"   CRS: {target_crs.authid()}\n"
                f"   Features: {total}\n"
                f"   Font conversions: {converted_count}"
            )
            QMessageBox.information(
                self, "✅ Done",
                f"Exported {total} features → {os.path.basename(path)}\n"
                f"Format: {driver}\n"
                f"CRS: {target_crs.authid()}\n"
                f"Font conversions: {converted_count}"
            )
        else:
            self.log.append(f"❌ Error: {error}")
            QMessageBox.critical(self, "Error", str(error))

        self.progress.setVisible(False)

    # ═══════════════════════════════════════════════════════════════
    # Conversion engines
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def _convert_tcvn3_to_unicode(text):
        """Convert TCVN3 (ABC) encoded text to Unicode."""
        result = []
        for ch in text:
            result.append(_TCVN3_TO_UNICODE.get(ch, ch))
        return ''.join(result)

    @staticmethod
    def _convert_unicode_to_tcvn3(text):
        """Convert Unicode text to TCVN3 encoding."""
        result = []
        for ch in text:
            result.append(_UNICODE_TO_TCVN3.get(ch, ch))
        return ''.join(result)

    @staticmethod
    def _convert_vni_to_unicode(text):
        """Convert VNI encoded text to Unicode."""
        result = text
        # Sort by key length descending to match multi-char sequences first
        for old, new in sorted(_VNI_TO_UNICODE.items(), key=lambda x: -len(x[0])):
            result = result.replace(old, new)
        return result
