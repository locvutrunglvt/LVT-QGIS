# -*- coding: utf-8 -*-
"""
LVT Font Converter — Convert font encoding for a vector layer and export.

Supports:
  - TCVN3 (ABC) → Unicode
  - VNI → Unicode
  - Unicode → TCVN3 (.VnTime for MapInfo)
  - No conversion (re-export with format/CRS change)
  - Export to SHP (with .cpg) or MapInfo TAB

Mapping tables based on u-convert (https://github.com/anhskohbo/u-convert)
and vietunicode.sourceforge.net/charset standard.

Author: Lộc Vũ Trung (LVT)
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
# TCVN3 ↔ Unicode mapping (134 chars, from u-convert reference)
# TCVN3 uppercase = multi-byte (base-char + accent-byte)
# TCVN3 lowercase = single accent-byte
# ═══════════════════════════════════════════════════════════════

# Index-matched parallel arrays: _UNICODE_FULL[i] ↔ _TCVN3_FULL[i]
_UNICODE_FULL = [
    'À','Á','Â','Ã','È','É','Ê','Ì','Í','Ò',
    'Ó','Ô','Õ','Ù','Ú','Ý','à','á','â','ã',
    'è','é','ê','ì','í','ò','ó','ô','õ','ù',
    'ú','ý','Ă','ă','Đ','đ','Ĩ','ĩ','Ũ','ũ',
    'Ơ','ơ','Ư','ư','Ạ','ạ','Ả','ả','Ấ','ấ',
    'Ầ','ầ','Ẩ','ẩ','Ẫ','ẫ','Ậ','ậ','Ắ','ắ',
    'Ằ','ằ','Ẳ','ẳ','Ẵ','ẵ','Ặ','ặ','Ẹ','ẹ',
    'Ẻ','ẻ','Ẽ','ẽ','Ế','ế','Ề','ề','Ể','ể',
    'Ễ','ễ','Ệ','ệ','Ỉ','ỉ','Ị','ị','Ọ','ọ',
    'Ỏ','ỏ','Ố','ố','Ồ','ồ','Ổ','ổ','Ỗ','ỗ',
    'Ộ','ộ','Ớ','ớ','Ờ','ờ','Ở','ở','Ỡ','ỡ',
    'Ợ','ợ','Ụ','ụ','Ủ','ủ','Ứ','ứ','Ừ','ừ',
    'Ử','ử','Ữ','ữ','Ự','ự','Ỳ','ỳ','Ỵ','ỵ',
    'Ỷ','ỷ','Ỹ','ỹ',
]

_TCVN3_FULL = [
    'A\xb5','A\xb8','\xa2','A\xb7','E\xcc','E\xd0','\xa3','I\xd7','I\xdd','O\xdf',
    'O\xe3','\xa4','O\xe2','U\xef','U\xf3','Y\xfd','\xb5','\xb8','\xa9','\xb7',
    '\xcc','\xd0','\xaa','\xd7','\xdd','\xdf','\xe3','\xab','\xe2','\xef',
    '\xf3','\xfd','\xa1','\xa8','\xa7','\xae','I\xdc','\xdc','U\xf2','\xf2',
    '\xa5','\xac','\xa6','\xad','A\xb9','\xb9','A\xb6','\xb6','\xa2\xca','\xca',
    '\xa2\xc7','\xc7','\xa2\xc8','\xc8','\xa2\xc9','\xc9','\xa2\xcb','\xcb','\xa1\xbe','\xbe',
    '\xa1\xbb','\xbb','\xa1\xbc','\xbc','\xa1\xbd','\xbd','\xa1\xc6','\xc6','E\xd1','\xd1',
    'E\xce','\xce','E\xcf','\xcf','\xa3\xd5','\xd5','\xa3\xd2','\xd2','\xa3\xd3','\xd3',
    '\xa3\xd4','\xd4','\xa3\xd6','\xd6','I\xd8','\xd8','I\xde','\xde','O\xe4','\xe4',
    'O\xe1','\xe1','\xa4\xe8','\xe8','\xa4\xe5','\xe5','\xa4\xe6','\xe6','\xa4\xe7','\xe7',
    '\xa4\xe9','\xe9','\xa5\xed','\xed','\xa5\xea','\xea','\xa5\xeb','\xeb','\xa5\xec','\xec',
    '\xa5\xee','\xee','U\xf4','\xf4','U\xf1','\xf1','\xa6\xf8','\xf8','\xa6\xf5','\xf5',
    '\xa6\xf6','\xf6','\xa6\xf7','\xf7','\xa6\xf9','\xf9','Y\xfa','\xfa','Y\xfe','\xfe',
    'Y\xfb','\xfb','Y\xfc','\xfc',
]

# Build lookup dicts — sort by length desc for multi-byte priority
_UNI2TCVN = {}
_TCVN2UNI = {}
for _i in range(len(_UNICODE_FULL)):
    _u = _UNICODE_FULL[_i]
    _t = _TCVN3_FULL[_i]
    _UNI2TCVN[_u] = _t
    _TCVN2UNI[_t] = _u

# Sort TCVN3→Unicode by key length descending (multi-byte first)
_TCVN2UNI_SORTED = sorted(_TCVN2UNI.items(), key=lambda x: len(x[0]), reverse=True)

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
        """Convert text fields in memory, then write using QgsVectorFileWriter."""
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

        # --- Write features with QgsVectorFileWriter (always UTF-8) ---
        writer = QgsVectorFileWriter(
            path, "UTF-8",
            layer.fields(), layer.wkbType(), layer.crs(),
            driver
        )

        if writer.hasError() != QgsVectorFileWriter.NoError:
            self.log.append(f"❌ Writer error: {writer.errorMessage()}")
            QMessageBox.critical(self, "Error", writer.errorMessage())
            del writer
            return

        converted_count = 0
        for i, feat in enumerate(features):
            self.progress.setValue(i + 1)

            # Convert text fields
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

            writer.addFeature(feat)

        del writer  # Close and flush

        self.log.append(f"🔤 Converted: {converted_count} values")
        self.progress.setValue(total + 2)
        QApplication.processEvents()

        # --- Post-process for MapInfo TAB: patch charset + re-encode .DAT ---
        if driver == "MapInfo File":
            self._postprocess_tab(path)

        # --- Write .cpg file for SHP ---
        if driver == "ESRI Shapefile":
            cpg_path = os.path.splitext(path)[0] + ".cpg"
            try:
                with open(cpg_path, 'w') as f:
                    f.write("UTF-8")
                self.log.append(f"📄 Created {os.path.basename(cpg_path)} (UTF-8)")
            except Exception as e:
                self.log.append(f"⚠️ Could not write .cpg: {e}")

        # --- Load result & set encoding ---
        load_enc = 'System' if driver == 'MapInfo File' else 'UTF-8'
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
        if mode == 2:
            tip = (
                "\n💡 Mở trong MapInfo:\n"
                "   Font: .VnTime / .VnArial\n"
                "   Mở trực tiếp — encoding WindowsLatin1"
            )

        QMessageBox.information(
            self, "✅ Done / Hoàn thành",
            f"Exported {total} features → {os.path.basename(path)}\n"
            f"Format: {driver}\n"
            f"CRS: {crs_str}\n"
            f"Font conversions: {converted_count}"
            + tip
        )

    def _postprocess_tab(self, tab_path):
        """Post-process TAB files for MapInfo compatibility.

        QgsVectorFileWriter always writes Charset "Neutral" regardless of
        the encoding parameter. This method:
        1. Patches .TAB header: Neutral → WindowsLatin1
        2. Re-encodes .DAT text fields: UTF-8 multi-byte → single-byte
           using dBASE record structure (preserves fixed-width fields).
        """
        import struct

        # Step 1: Patch .TAB header charset
        try:
            with open(tab_path, 'r', encoding='ascii', errors='replace') as f:
                header = f.read()
            patched = header.replace(
                'Charset "Neutral"', 'Charset "WindowsLatin1"'
            ).replace(
                '!charset Neutral', '!charset WindowsLatin1'
            )
            if patched != header:
                with open(tab_path, 'w', encoding='ascii', errors='replace') as f:
                    f.write(patched)
                self.log.append('📝 .TAB charset: Neutral → WindowsLatin1')
        except Exception as e:
            self.log.append(f'⚠️ Could not patch .TAB header: {e}')

        # Step 2: Re-encode .DAT file (dBASE III format)
        dat_path = os.path.splitext(tab_path)[0] + '.dat'
        if not os.path.exists(dat_path):
            return

        try:
            with open(dat_path, 'rb') as f:
                data = bytearray(f.read())

            if len(data) < 32:
                return

            # Parse dBASE header
            num_records = struct.unpack_from('<I', data, 4)[0]
            header_size = struct.unpack_from('<H', data, 8)[0]
            record_size = struct.unpack_from('<H', data, 10)[0]

            # Parse field descriptors (32 bytes each, starting at byte 32)
            fields = []
            offset = 32
            while offset < header_size - 1 and data[offset] != 0x0D:
                fname = data[offset:offset+11].split(b'\x00')[0].decode('ascii', errors='replace')
                ftype = chr(data[offset+11])
                flen = data[offset+16]
                fields.append((fname, ftype, flen))
                offset += 32

            # Process each record
            n_fixed = 0
            for rec_idx in range(num_records):
                rec_start = header_size + rec_idx * record_size
                field_offset = 1  # Skip deletion flag byte

                for fname, ftype, flen in fields:
                    fstart = rec_start + field_offset
                    fend = fstart + flen

                    if ftype == 'C' and fend <= len(data):
                        # Character field: decode UTF-8 → re-encode latin-1
                        raw = bytes(data[fstart:fend])
                        try:
                            text = raw.decode('utf-8')
                            # Encode as latin-1 (covers U+0000-U+00FF)
                            latin = text.encode('latin-1', errors='replace')
                            # Pad to original field width with spaces
                            padded = latin[:flen].ljust(flen, b' ')
                            if padded != raw:
                                data[fstart:fend] = padded
                                n_fixed += 1
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            pass  # Leave field as-is if conversion fails

                    field_offset += flen

            if n_fixed > 0:
                with open(dat_path, 'wb') as f:
                    f.write(bytes(data))
                self.log.append(f'🔧 Re-encoded {n_fixed} fields (UTF-8 → latin-1) in .DAT')
            else:
                self.log.append('📝 .DAT: no re-encoding needed')

        except Exception as e:
            self.log.append(f'⚠️ Could not re-encode .DAT: {e}')

    # ═══════════════════════════════════════════════════════════════
    # Conversion engines (u-convert reference, multi-byte aware)
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def _convert_tcvn3_to_unicode(text):
        """TCVN3 → Unicode: multi-byte sequences first, then single-byte."""
        for tcvn_seq, uni_char in _TCVN2UNI_SORTED:
            if tcvn_seq in text:
                text = text.replace(tcvn_seq, uni_char)
        return text

    @staticmethod
    def _convert_unicode_to_tcvn3(text):
        """Unicode → TCVN3: single Unicode char → 1 or 2 byte TCVN3 sequence."""
        result = []
        for ch in text:
            if ch in _UNI2TCVN:
                result.append(_UNI2TCVN[ch])
            else:
                result.append(ch)
        return ''.join(result)

    @staticmethod
    def _convert_vni_to_unicode(text):
        """VNI → Unicode: multi-char sequences first, then single-char."""
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
        _vni1 = [
            ('ñ','đ'),('Ñ','Đ'),('í','í'),('Í','Í'),
            ('ì','ì'),('Ì','Ì'),('æ','ỉ'),('Æ','Ỉ'),
            ('ö','ư'),('Ö','Ư'),('î','ỵ'),('Î','Ỵ'),
        ]
        for old, new in _vni2:
            text = text.replace(old, new)
        for old, new in _vni1:
            text = text.replace(old, new)
        return text
