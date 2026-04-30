# -*- coding: utf-8 -*-
"""
LVT Font Converter — Convert font encoding for a vector layer and export.

Supports:
  - TCVN3 (ABC) → Unicode
  - VNI → Unicode
  - Unicode → TCVN3 (.VnTime for MapInfo)
  - No conversion (re-export with format/CRS change)
  - Export to SHP (with .cpg) or MapInfo TAB

Mapping tables based on standard Vietnamese encoding specifications.

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
# Parallel encoding lists (standard Vietnamese font mapping)
# Index-matched: _UNICODE[i] ↔ _TCVN3[i]
# ═══════════════════════════════════════════════════════════════
_UNICODE = [
    'â','Â','ă','Ă','đ','Đ','ê','Ê','ô','Ô','ơ','Ơ','ư','Ư',
    'á','Á','à','À','ả','Ả','ã','Ã','ạ','Ạ',
    'ấ','Ấ','ầ','Ầ','ẩ','Ẩ','ẫ','Ẫ','ậ','Ậ',
    'ắ','Ắ','ằ','Ằ','ẳ','Ẳ','ẵ','Ẵ','ặ','Ặ',
    'é','É','è','È','ẻ','Ẻ','ẽ','Ẽ','ẹ','Ẹ',
    'ế','Ế','ề','Ề','ể','Ể','ễ','Ễ','ệ','Ệ',
    'í','Í','ì','Ì','ỉ','Ỉ','ĩ','Ĩ','ị','Ị',
    'ó','Ó','ò','Ò','ỏ','Ỏ','õ','Õ','ọ','Ọ',
    'ố','Ố','ồ','Ồ','ổ','Ổ','ỗ','Ỗ','ộ','Ộ',
    'ớ','Ớ','ờ','Ờ','ở','Ở','ỡ','Ỡ','ợ','Ợ',
    'ú','Ú','ù','Ù','ủ','Ủ','ũ','Ũ','ụ','Ụ',
    'ứ','Ứ','ừ','Ừ','ử','Ử','ữ','Ữ','ự','Ự',
    'ỳ','Ỳ','ỷ','Ỷ','ỹ','Ỹ','ỵ','Ỵ','ý','Ý',
]

_TCVN3 = [
    '©','¢','¨','¡','®','§','ª','£','«','¤','¬','¥','\xad','¦',
    '¸','¸','µ','µ','¶','¶','·','·','¹','¹',
    'Ê','Ê','Ç','Ç','È','È','É','É','Ë','Ë',
    '¾','¾','»','»','¼','¼','½','½','Æ','Æ',
    'Ð','Ð','Ì','Ì','Î','Î','Ï','Ï','Ñ','Ñ',
    'Õ','Õ','Ò','Ò','Ó','Ó','Ô','Ô','Ö','Ö',
    'Ý','Ý','×','×','Ø','Ø','Ü','Ü','Þ','Þ',
    'ã','ã','ß','ß','á','á','â','â','ä','ä',
    'è','è','å','å','æ','æ','ç','ç','é','é',
    'í','í','ê','ê','ë','ë','ì','ì','î','î',
    'ó','ó','ï','ï','ñ','ñ','ò','ò','ô','ô',
    'ø','ø','õ','õ','ö','ö','÷','÷','ù','ù',
    'ú','ú','û','û','ü','ü','þ','þ','ý','ý',
]

# Build fast lookup dicts from the parallel lists
_UNI2TCVN = {}
_TCVN2UNI = {}
for _i, _u in enumerate(_UNICODE):
    _t = _TCVN3[_i]
    _UNI2TCVN[_u] = _t
    # For TCVN3→Unicode, TCVN3 has duplicate chars for upper/lower
    # (e.g. '¸' maps to both 'á' and 'Á'). We keep the first (lowercase).
    if _t not in _TCVN2UNI:
        _TCVN2UNI[_t] = _u

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

        # --- Mode: 0=TCVN3→Uni, 1=VNI→Uni, 2=Uni→TCVN3, 3=none ---
        mode = self.cmb_from.currentIndex()

        # --- Format: 0=SHP, 1=TAB ---
        fmt_idx = self.cmb_format.currentIndex()
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
            import traceback
            self.log.append(traceback.format_exc())
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.btn_convert.setEnabled(True)
            self.progress.setVisible(False)

    def _export(self, layer, path, driver, ext, mode, target_crs):
        """Convert text fields, then write to file.

        SHP: uses QgsVectorFileWriter with UTF-8 + .cpg
        TAB: uses osgeo.ogr directly with latin-1 encoding to preserve
             ALL byte values (including 0xAD soft-hyphen = TCVN3 'ư').
        """
        # Identify string fields
        fields_list = []
        for field in layer.fields():
            if field.type() == QVariant.String:
                fields_list.append(field.name())

        features = list(layer.getFeatures())
        total = len(features)
        self.progress.setMaximum(total + 5)

        mode_labels = [
            "TCVN3 → Unicode", "VNI → Unicode",
            "Unicode → TCVN3", "No conversion",
        ]
        self.log.append(f"📋 Layer: {layer.name()} — {total} features")
        self.log.append(f"🔤 Text fields: {len(fields_list)} ({', '.join(fields_list[:5])})")
        self.log.append(f"🔄 Mode: {mode_labels[mode]}")
        self.log.append(f"💾 Format: {driver}")
        QApplication.processEvents()

        # --- Convert all text values first ---
        converted_count = 0
        for feat in features:
            if mode < 3:
                for fn in fields_list:
                    old_val = feat[fn]
                    if old_val is not None and isinstance(old_val, str) and old_val:
                        if mode == 0:
                            new_val = self._convert_tcvn3_to_unicode(old_val)
                        elif mode == 1:
                            new_val = self._convert_vni_to_unicode(old_val)
                        elif mode == 2:
                            new_val = self._convert_unicode_to_tcvn3(old_val)
                        else:
                            new_val = old_val
                        if new_val != old_val:
                            converted_count += 1
                            feat[fn] = new_val

        self.log.append(f"🔤 Converted: {converted_count} values")
        QApplication.processEvents()

        # --- Write to file ---
        if driver == "MapInfo File":
            self._write_tab(layer, features, path)
        else:
            self._write_shp(layer, features, path)

        self.progress.setValue(total + 2)
        QApplication.processEvents()

        # --- Load result ---
        load_enc = "latin-1" if driver == "MapInfo File" else "UTF-8"
        try:
            result_layer = QgsVectorLayer(path, os.path.basename(path).replace(ext, ''), 'ogr')
            result_layer.setProviderEncoding('System')
            result_layer.dataProvider().setEncoding(load_enc)
            if result_layer.isValid():
                QgsProject.instance().addMapLayer(result_layer)
                self.log.append(f"✅ Added to project: {result_layer.name()}")
        except Exception as e:
            self.log.append(f"⚠️ Could not add layer: {e}")

        self.progress.setValue(total + 5)

        crs_str = layer.crs().authid()
        self.log.append(
            f"\n✅ HOÀN THÀNH!\n"
            f"   File: {os.path.basename(path)}\n"
            f"   CRS: {crs_str}\n"
            f"   Features: {total}\n"
            f"   Font conversions: {converted_count}\n"
            f"   Encoding: {load_enc}"
        )

        tip = ""
        if mode == 2 and driver == "MapInfo File":
            tip = (
                "\n💡 Mở trong MapInfo:\n"
                "   Font: .VnTime / .VnArial\n"
                "   Dữ liệu đã encode WindowsLatin1 — mở trực tiếp!"
            )

        QMessageBox.information(
            self, "✅ Done / Hoàn thành",
            f"Exported {total} features → {os.path.basename(path)}\n"
            f"Format: {driver}\n"
            f"CRS: {crs_str}\n"
            f"Font conversions: {converted_count}"
            + tip
        )

    def _write_shp(self, layer, features, path):
        """Write SHP with QgsVectorFileWriter + UTF-8 + .cpg."""
        writer = QgsVectorFileWriter(
            path, "UTF-8",
            layer.fields(), layer.wkbType(), layer.crs(),
            "ESRI Shapefile"
        )
        if writer.hasError() != QgsVectorFileWriter.NoError:
            self.log.append(f"❌ Writer error: {writer.errorMessage()}")
            del writer
            return
        for i, feat in enumerate(features):
            self.progress.setValue(i + 1)
            writer.addFeature(feat)
        del writer

        cpg_path = os.path.splitext(path)[0] + ".cpg"
        try:
            with open(cpg_path, 'w') as f:
                f.write("UTF-8")
            self.log.append(f"📄 Created {os.path.basename(cpg_path)} (UTF-8)")
        except Exception as e:
            self.log.append(f"⚠️ Could not write .cpg: {e}")

    def _write_tab(self, layer, features, path):
        """Write TAB: QgsVectorFileWriter (UTF-8) + binary re-encode.

        Step 1: Write TAB with UTF-8 (preserves ALL chars including U+00AD)
        Step 2: Re-encode .DAT text data from UTF-8 → latin-1 single bytes
        Step 3: Patch .TAB header charset: UTF-8 → WindowsLatin1

        This ensures MapInfo reads the file natively with .VnTime font.
        """
        self.log.append("📝 Writing TAB (QgsVectorFileWriter + re-encode)")

        # Step 1: Write with QgsVectorFileWriter (UTF-8)
        writer = QgsVectorFileWriter(
            path, "UTF-8",
            layer.fields(), layer.wkbType(), layer.crs(),
            "MapInfo File"
        )
        if writer.hasError() != QgsVectorFileWriter.NoError:
            self.log.append(f"❌ Writer error: {writer.errorMessage()}")
            del writer
            return
        for i, feat in enumerate(features):
            self.progress.setValue(i + 1)
            writer.addFeature(feat)
        del writer

        # Step 2: Re-encode .DAT file from UTF-8 to latin-1
        dat_path = os.path.splitext(path)[0] + '.dat'
        if os.path.exists(dat_path):
            try:
                with open(dat_path, 'rb') as f:
                    data = f.read()

                # Replace UTF-8 two-byte sequences (C2 80..C3 BF) with
                # their single-byte latin-1 equivalents (80..FF).
                # UTF-8: C2 xx -> byte xx (for 0x80-0xBF)
                # UTF-8: C3 xx -> byte (xx + 0x40) (for 0xC0-0xFF)
                out = bytearray()
                idx = 0
                n_fixed = 0
                while idx < len(data):
                    b = data[idx]
                    if b == 0xC2 and idx + 1 < len(data) and 0x80 <= data[idx+1] <= 0xBF:
                        out.append(data[idx+1])
                        idx += 2
                        n_fixed += 1
                    elif b == 0xC3 and idx + 1 < len(data) and 0x80 <= data[idx+1] <= 0xBF:
                        out.append(data[idx+1] + 0x40)
                        idx += 2
                        n_fixed += 1
                    else:
                        out.append(b)
                        idx += 1

                if n_fixed > 0:
                    with open(dat_path, 'wb') as f:
                        f.write(bytes(out))
                    self.log.append(f"🔧 Re-encoded {n_fixed} chars (UTF-8 → latin-1) in .DAT")
            except Exception as e:
                self.log.append(f"⚠️ Could not re-encode .DAT: {e}")

        # Step 3: Patch .TAB header charset
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='ascii', errors='replace') as f:
                    header = f.read()
                patched = header.replace('Charset "UTF-8"', 'Charset "WindowsLatin1"')
                if patched != header:
                    with open(path, 'w', encoding='ascii', errors='replace') as f:
                        f.write(patched)
                    self.log.append('📝 Patched .TAB charset: UTF-8 → WindowsLatin1')
            except Exception as e:
                self.log.append(f"⚠️ Could not patch .TAB header: {e}")

        self.log.append(f"✅ TAB file written: {os.path.basename(path)}")

    # ═══════════════════════════════════════════════════════════════
    # Conversion engines (index-based parallel list approach)
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def _convert_tcvn3_to_unicode(text):
        """TCVN3 → Unicode: replace each TCVN3 char with its Unicode equivalent."""
        result = ''
        for ch in text:
            if ch in _TCVN2UNI:
                result += _TCVN2UNI[ch]
            else:
                result += ch
        return result

    @staticmethod
    def _convert_unicode_to_tcvn3(text):
        """Unicode → TCVN3: replace each Unicode Vietnamese char with TCVN3 equivalent."""
        result = ''
        for ch in text:
            if ch in _UNI2TCVN:
                result += _UNI2TCVN[ch]
            else:
                result += ch
        return result

    @staticmethod
    def _convert_vni_to_unicode(text):
        """VNI → Unicode: multi-char sequences first, then single-char."""
        # 2-char sequences
        _vni2 = [
            ('aâ','â'),('AÂ','Â'),('aê','ă'),('AÊ','Ă'),('eâ','ê'),('EÂ','Ê'),
            ('aù','á'),('AÙ','Á'),('aø','à'),('AØ','À'),('aû','ả'),('AÛ','Ả'),
            ('aõ','ã'),('AÕ','Ã'),('aï','ạ'),('AÏ','Ạ'),
            ('aá','ấ'),('AÁ','Ấ'),('aà','ầ'),('AÀ','Ầ'),('aå','ẩ'),('AÅ','Ẩ'),
            ('aã','ẫ'),('AÃ','Ẫ'),('aä','ậ'),('AÄ','Ậ'),
            ('aé','ắ'),('AÉ','Ắ'),('aè','ằ'),('AÈ','Ằ'),('aú','ẳ'),('AÚ','Ẳ'),
            ('aü','ẵ'),('AÜ','Ẵ'),('aë','ặ'),('AË','Ặ'),
            ('eù','é'),('EÙ','É'),('eø','è'),('EØ','È'),('eû','ẻ'),('EÛ','Ẻ'),
            ('eõ','ẽ'),('EÕ','Ẽ'),('eï','ẹ'),('EÏ','Ẹ'),
            ('eá','ế'),('EÁ','Ế'),('eà','ề'),('EÀ','Ề'),('eå','ể'),('EÅ','Ể'),
            ('eã','ễ'),('EÃ','Ễ'),('eä','ệ'),('EÄ','Ệ'),
            ('oû','ỏ'),('OÛ','Ỏ'),('oõ','õ'),('OÕ','Õ'),('oï','ọ'),('OÏ','Ọ'),
            ('oá','ố'),('OÁ','Ố'),('oà','ồ'),('OÀ','Ồ'),('oå','ổ'),('OÅ','Ổ'),
            ('oã','ỗ'),('OÃ','Ỗ'),('oä','ộ'),('OÄ','Ộ'),
            ('ôù','ớ'),('ÔÙ','Ớ'),('ôø','ờ'),('ÔØ','Ờ'),('ôû','ở'),('ÔÛ','Ở'),
            ('ôõ','ỡ'),('ÔÕ','Ỡ'),('ôï','ợ'),('ÔÏ','Ợ'),
            ('uù','ú'),('UÙ','Ú'),('uø','ù'),('UØ','Ù'),('uû','ủ'),('UÛ','Ủ'),
            ('uõ','ũ'),('UÕ','Ũ'),('uï','ụ'),('UÏ','Ụ'),
            ('öù','ứ'),('ÖÙ','Ứ'),('öø','ừ'),('ÖØ','Ừ'),('öû','ử'),('ÖÛ','Ử'),
            ('öõ','ữ'),('ÖÕ','Ữ'),('öï','ự'),('ÖÏ','Ự'),
            ('yø','ỳ'),('YØ','Ỳ'),('yû','ỷ'),('YÛ','Ỷ'),
            ('yõ','ỹ'),('YÕ','Ỹ'),('yù','ý'),('YÙ','Ý'),
            ('où','ó'),('OÙ','Ó'),('oø','ò'),('OØ','Ò'),('oâ','ô'),('OÂ','Ô'),
        ]
        # 1-char sequences
        _vni1 = [
            ('ñ','đ'),('Ñ','Đ'),('í','í'),('Í','Í'),
            ('ì','ì'),('Ì','Ì'),('æ','ỉ'),('Æ','Ỉ'),
            ('ö','ư'),('Ö','Ư'),('î','ỵ'),('Î','Ỵ'),
        ]
        # Apply 2-char first
        for old, new in _vni2:
            text = text.replace(old, new)
        for old, new in _vni1:
            text = text.replace(old, new)
        return text
