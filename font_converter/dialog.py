# -*- coding: utf-8 -*-
"""
LVT Font Converter — Convert font encoding for a vector layer and export to SHP.

Common use case: Vietnamese forestry data stored in TCVN3 / VNI font encoding
needs conversion to Unicode before spatial analysis.

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

# Vietnamese legacy font mapping tables
# TCVN3 (ABC) → Unicode mapping
TCVN3_MAP = {
    'a¨':'ă','a©':'ắ','a¾':'ằ','a½':'ẳ','a»':'ẵ','a¼':'ặ',
    'a©':'ắ','©':'Ắ','¨':'Ă',
    'aâ':'â','Êy':'ấ','Çu':'ầ','È':'ẩ','É':'ẫ','Ë':'ậ',
    'e':'ê','Õ':'ế','Ò':'ề','Ó':'ể','Ô':'ễ','Ö':'ệ',
    'i':'i','Ý':'í','×':'ì','Ø':'ỉ','Ü':'ĩ','Þ':'ị',
    'o':'ô','è':'ố','å':'ồ','æ':'ổ','ç':'ỗ','é':'ộ',
    '¬':'ơ','í':'ớ','ê':'ờ','ë':'ở','ì':'ỡ','î':'ợ',
    'u':'u','ó':'ú','ï':'ù','ð':'ủ','ò':'ũ','ô':'ụ',
    '­':'ư','ø':'ứ','õ':'ừ','ö':'ử','÷':'ữ','ù':'ự',
    'y':'y','ý':'ý','ú':'ỳ','û':'ỷ','ü':'ỹ','þ':'ỵ',
    '®':'đ','§':'Đ',
}

# VNI → Unicode mapping  (simplified — covers most common chars)
VNI_MAP = {
    'aê':'ă','aé':'ắ','aè':'ằ','aú':'ẳ','aû':'ẵ','aë':'ặ',
    'aâ':'â','aá':'ấ','aà':'ầ','aå':'ẩ','aã':'ẫ','aä':'ậ',
    'eâ':'ê','eá':'ế','eà':'ề','eå':'ể','eã':'ễ','eä':'ệ',
    'oâ':'ô','oá':'ố','oà':'ồ','oå':'ổ','oã':'ỗ','oä':'ộ',
    'ô':'ơ','ôù':'ớ','ôø':'ờ','ôû':'ở','ôõ':'ỡ','ôï':'ợ',
    'ö':'ư','öù':'ứ','öø':'ừ','öû':'ử','öõ':'ữ','öï':'ự',
    'ñ':'đ','Ñ':'Đ',
    'aù':'á','aø':'à','aû':'ả','aõ':'ã','aï':'ạ',
    'eù':'é','eø':'è','eû':'ẻ','eõ':'ẽ','eï':'ẹ',
    'ó':'í','ì':'ì','æ':'ỉ','ó':'ĩ','ò':'ị',
    'où':'ó','oø':'ò','oû':'ỏ','oõ':'õ','oï':'ọ',
    'uù':'ú','uø':'ù','uû':'ủ','uõ':'ũ','uï':'ụ',
    'yù':'ý','yø':'ỳ','yû':'ỷ','yõ':'ỹ','î':'ỵ',
}

# CRS list (shared across modules)
from .._crs_list import CRS_LIST


class FontConverterDialog(QDialog):
    """Font Converter: change encoding + export SHP with CRS."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("LVT — Font Converter / Chuyển đổi Font")
        self.setMinimumSize(560, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        ly = QVBoxLayout(self)

        # Header
        hdr = QLabel("<h3>🔤 Font Converter / Chuyển đổi Font chữ</h3>")
        ly.addWidget(hdr)
        ly.addWidget(QLabel(
            "Chuyển font TCVN3/VNI sang Unicode cho layer và xuất Shapefile."
        ))

        form = QFormLayout()

        # Layer
        self.cmb_layer = QgsMapLayerComboBox()
        form.addRow("Layer:", self.cmb_layer)

        # Source encoding
        self.cmb_from = QComboBox()
        self.cmb_from.addItems([
            "TCVN3 (ABC) → Unicode",
            "VNI → Unicode",
            "Unicode (no conversion)",
        ])
        form.addRow("Font nguồn / Source:", self.cmb_from)

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
        self.log.setMaximumHeight(120)
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

        # Get encoding mode
        mode = self.cmb_from.currentIndex()

        # Output path
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Shapefile", "", "Shapefile (*.shp)"
        )
        if not path:
            return

        self.progress.setVisible(True)
        self.log.setVisible(True)
        self.log.clear()

        # Create memory layer with converted text
        features = list(layer.getFeatures())
        total = len(features)
        self.progress.setMaximum(total)

        fields = layer.fields()
        text_field_indices = [
            i for i in range(fields.count())
            if fields.field(i).typeName().lower() in ('string', 'text', 'varchar')
        ]

        converted = 0
        new_features = []
        for i, feat in enumerate(features):
            self.progress.setValue(i + 1)
            new_feat = QgsFeature(feat)
            attrs = list(feat.attributes())
            for fi in text_field_indices:
                val = attrs[fi]
                if isinstance(val, str) and val:
                    if mode == 0:
                        attrs[fi] = self._convert_tcvn3(val)
                    elif mode == 1:
                        attrs[fi] = self._convert_vni(val)
                    if attrs[fi] != val:
                        converted += 1
            new_feat.setAttributes(attrs)
            new_features.append(new_feat)

        # Write to shapefile
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        ctx = QgsCoordinateTransformContext()
        if layer.crs() != target_crs:
            ctx.addCoordinateOperation(layer.crs(), target_crs, "")

        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, path, ctx, options
        )

        if error[0] == QgsVectorFileWriter.NoError:
            # If conversion was done, overwrite text fields in output
            if mode < 2 and converted > 0:
                out_layer = QgsVectorLayer(path, "temp", "ogr")
                if out_layer.isValid():
                    out_layer.startEditing()
                    for i, new_feat in enumerate(new_features):
                        fid = i + 1  # Shapefile FIDs are 1-based typically
                        for fi in text_field_indices:
                            out_layer.changeAttributeValue(
                                fid, fi, new_feat.attributes()[fi]
                            )
                    out_layer.commitChanges()

            # Add to project
            result_layer = QgsVectorLayer(
                path, os.path.basename(path).replace('.shp', ''), "ogr"
            )
            if result_layer.isValid():
                QgsProject.instance().addMapLayer(result_layer)

            self.log.append(
                f"✅ Exported: {os.path.basename(path)}\n"
                f"   CRS: {target_crs.authid()}\n"
                f"   Features: {total}\n"
                f"   Text fields converted: {converted}"
            )
            QMessageBox.information(
                self, "✅ Done",
                f"Exported {total} features to {os.path.basename(path)}\n"
                f"CRS: {target_crs.authid()}\n"
                f"Font conversions: {converted}"
            )
        else:
            self.log.append(f"❌ Error: {error}")
            QMessageBox.critical(self, "Error", str(error))

    @staticmethod
    def _convert_tcvn3(text):
        """Convert TCVN3 encoded text to Unicode."""
        result = text
        for old, new in sorted(TCVN3_MAP.items(), key=lambda x: -len(x[0])):
            result = result.replace(old, new)
        return result

    @staticmethod
    def _convert_vni(text):
        """Convert VNI encoded text to Unicode."""
        result = text
        for old, new in sorted(VNI_MAP.items(), key=lambda x: -len(x[0])):
            result = result.replace(old, new)
        return result
