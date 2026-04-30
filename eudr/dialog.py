# -*- coding: utf-8 -*-
"""
LVT EUDR Module — GeoJSON Export Dialog.

Provides a complete UI for exporting QGIS vector layers to
EUDR-compliant GeoJSON format (EU Regulation 2023/1115).

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""

import os

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QComboBox, QLineEdit, QPushButton, QSpinBox,
    QDoubleSpinBox, QFileDialog, QMessageBox, QGroupBox,
    QFormLayout, QCheckBox, QScrollArea, QFrame, QTextEdit,
)
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

from .eudr_i18n import tr as eudr_tr, get_guide
from .geojson_builder import (
    EudrGeoJsonBuilder,
    MODE_EUDR_MIXED, MODE_ALL_POINTS, MODE_ALL_POLYGONS,
    MODE_POINT_UNDER_4, MODE_POLY_OVER_4,
)


class EudrExportDialog(QDialog):
    """EUDR GeoJSON Export Dialog.

    Provides:
        - Layer selection with geometry/CRS info
        - EUDR field mapping (combo boxes for each EUDR property)
        - Export settings (precision, area threshold)
        - Preview statistics
        - Guide/Help tab
        - Author tab
    """

    # EUDR required/optional fields
    EUDR_FIELDS = [
        ("ProductionPlace", "Production Place:", True),
        ("Country", "Country of Production:", True),
        ("PlotID", "Plot ID:", True),
        ("Area_ha", "Area (ha):", True),
        ("Latitude", "Latitude:", True),
        ("Longitude", "Longitude:", True),
        ("ProductDescription", "Product Description:", False),
        ("HSCode", "HS Code:", False),
        ("OperatorName", "Operator Name:", False),
        ("ProductionDate", "Date of Production:", False),
    ]

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.lang = 'vi'
        self._field_combos = {}
        self._manual_edits = {}

        self.setMinimumSize(750, 650)
        self.resize(850, 700)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )

        self._setup_ui()
        self._refresh_layers()
        self._refresh_ui_text()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """Build the complete dialog UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        # Language toggle
        top_bar = QHBoxLayout()
        self.btn_lang = QPushButton()
        self.btn_lang.setFixedWidth(110)
        self.btn_lang.clicked.connect(self._toggle_language)
        top_bar.addWidget(self.btn_lang)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Export
        self.tab_export = QWidget()
        self._setup_export_tab()
        self.tabs.addTab(self.tab_export, "")

        # Tab 2: Guide
        self.tab_guide = QWidget()
        self._setup_guide_tab()
        self.tabs.addTab(self.tab_guide, "")

        # Tab 3: Author
        self.tab_author = QWidget()
        self._setup_author_tab()
        self.tabs.addTab(self.tab_author, "")

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_close = QPushButton()
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)
        main_layout.addLayout(btn_layout)

    def _setup_export_tab(self):
        """Build the main export tab with scroll area."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)

        # --- 1. Layer Selection ---
        self.grp_layer = QGroupBox()
        ly1 = QFormLayout()

        self.cbo_layer = QComboBox()
        self.cbo_layer.currentIndexChanged.connect(self._on_layer_changed)
        ly1.addRow("", self.cbo_layer)

        self.lbl_geom_type = QLabel("—")
        self.lbl_feat_count = QLabel("—")
        self.lbl_layer_crs = QLabel("—")
        self.lbl_output_crs = QLabel("WGS84 (EPSG:4326)")
        self.lbl_output_crs.setStyleSheet("color: #1B5E20; font-weight: bold;")

        self.lbl_geom_type_label = QLabel()
        self.lbl_feat_count_label = QLabel()
        self.lbl_layer_crs_label = QLabel()
        self.lbl_output_crs_label = QLabel()

        ly1.addRow(self.lbl_geom_type_label, self.lbl_geom_type)
        ly1.addRow(self.lbl_feat_count_label, self.lbl_feat_count)
        ly1.addRow(self.lbl_layer_crs_label, self.lbl_layer_crs)
        ly1.addRow(self.lbl_output_crs_label, self.lbl_output_crs)

        self.grp_layer.setLayout(ly1)
        layout.addWidget(self.grp_layer)

        # --- 2. Field Mapping ---
        self.grp_fields = QGroupBox()
        ly2 = QFormLayout()

        for key, label, required in self.EUDR_FIELDS:
            row = QHBoxLayout()
            cbo = QComboBox()
            cbo.setMinimumWidth(200)
            row.addWidget(cbo, 3)

            txt = QLineEdit()
            txt.setPlaceholderText(
                "or type value..." if self.lang == 'en' else "hoặc nhập giá trị..."
            )
            txt.setEnabled(False)
            row.addWidget(txt, 2)

            self._field_combos[key] = cbo
            self._manual_edits[key] = txt

            # Connect: when combo selects "-- Manual value --", enable text input
            cbo.currentIndexChanged.connect(
                lambda idx, k=key: self._on_combo_changed(k)
            )

            lbl = QLabel()
            if required:
                lbl.setStyleSheet("font-weight: bold;")
            ly2.addRow(lbl, row)
            # Store label reference for i18n
            setattr(self, f"_lbl_{key}", lbl)

        self.grp_fields.setLayout(ly2)
        layout.addWidget(self.grp_fields)

        # --- 3. Export Settings ---
        self.grp_settings = QGroupBox()
        ly3 = QFormLayout()

        # Export mode selector
        self.cbo_export_mode = QComboBox()
        self.lbl_export_mode = QLabel()
        ly3.addRow(self.lbl_export_mode, self.cbo_export_mode)

        self.spn_precision = QSpinBox()
        self.spn_precision.setRange(6, 12)
        self.spn_precision.setValue(6)
        self.lbl_precision = QLabel()
        ly3.addRow(self.lbl_precision, self.spn_precision)

        self.spn_threshold = QDoubleSpinBox()
        self.spn_threshold.setRange(0.1, 100.0)
        self.spn_threshold.setValue(4.0)
        self.spn_threshold.setSuffix(" ha")
        self.spn_threshold.setDecimals(1)
        self.lbl_threshold = QLabel()
        ly3.addRow(self.lbl_threshold, self.spn_threshold)

        self.chk_validate = QCheckBox()
        self.chk_validate.setChecked(True)
        ly3.addRow("", self.chk_validate)

        self.chk_auto_area = QCheckBox()
        self.chk_auto_area.setChecked(True)
        ly3.addRow("", self.chk_auto_area)

        self.grp_settings.setLayout(ly3)
        layout.addWidget(self.grp_settings)

        # --- 4. Statistics ---
        self.grp_stats = QGroupBox()
        ly4 = QFormLayout()

        self.lbl_stat_total = QLabel("—")
        self.lbl_stat_point = QLabel("—")
        self.lbl_stat_poly = QLabel("—")
        self.lbl_stat_invalid = QLabel("—")

        self.lbl_st_total = QLabel()
        self.lbl_st_point = QLabel()
        self.lbl_st_poly = QLabel()
        self.lbl_st_invalid = QLabel()

        ly4.addRow(self.lbl_st_total, self.lbl_stat_total)
        ly4.addRow(self.lbl_st_point, self.lbl_stat_point)
        ly4.addRow(self.lbl_st_poly, self.lbl_stat_poly)
        ly4.addRow(self.lbl_st_invalid, self.lbl_stat_invalid)

        self.grp_stats.setLayout(ly4)
        layout.addWidget(self.grp_stats)

        # --- Action buttons ---
        action_ly = QHBoxLayout()
        self.btn_preview = QPushButton()
        self.btn_preview.clicked.connect(self._preview_statistics)
        self.btn_preview.setStyleSheet(
            "padding: 8px 16px; background-color: #2196F3; color: white; "
            "font-weight: bold; border-radius: 4px;"
        )
        action_ly.addWidget(self.btn_preview)

        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self._export_geojson)
        self.btn_export.setStyleSheet(
            "padding: 8px 16px; background-color: #1B5E20; color: white; "
            "font-weight: bold; border-radius: 4px;"
        )
        action_ly.addWidget(self.btn_export)
        layout.addLayout(action_ly)

        layout.addStretch()
        scroll.setWidget(content)

        tab_layout = QVBoxLayout(self.tab_export)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

    def _setup_guide_tab(self):
        """Build the guide/help tab."""
        layout = QVBoxLayout(self.tab_guide)
        self.txt_guide = QTextEdit()
        self.txt_guide.setReadOnly(True)
        layout.addWidget(self.txt_guide)

    def _setup_author_tab(self):
        """Build the author info tab."""
        layout = QVBoxLayout(self.tab_author)
        self.lbl_author = QLabel()
        self.lbl_author.setWordWrap(True)
        self.lbl_author.setTextFormat(Qt.RichText)
        self.lbl_author.setOpenExternalLinks(True)
        self.lbl_author.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.addWidget(self.lbl_author)
        layout.addStretch()

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def _t(self, text):
        """Translate using EUDR i18n with current language."""
        return eudr_tr(text, self.lang)

    def _toggle_language(self):
        """Toggle between English and Vietnamese."""
        self.lang = 'en' if self.lang == 'vi' else 'vi'
        self._refresh_ui_text()

    def _refresh_ui_text(self):
        """Update all UI text for current language."""
        self.setWindowTitle(
            "LVT — " + self._t("EUDR GeoJSON Export")
        )
        self.btn_lang.setText(
            "🌐 English" if self.lang == 'vi' else "🌐 Tiếng Việt"
        )

        # Tab titles
        self.tabs.setTabText(0, self._t("EUDR GeoJSON Export"))
        self.tabs.setTabText(1, self._t("Guide"))
        self.tabs.setTabText(2, self._t("Author"))

        # Group boxes
        self.grp_layer.setTitle(self._t("1. Select Layer"))
        self.grp_fields.setTitle(self._t("2. EUDR Field Mapping"))
        self.grp_settings.setTitle(self._t("3. Export Settings"))
        self.grp_stats.setTitle(self._t("4. Validation & Statistics"))

        # Layer info labels
        self.lbl_geom_type_label.setText(self._t("Geometry Type:"))
        self.lbl_feat_count_label.setText(self._t("Feature Count:"))
        self.lbl_layer_crs_label.setText(self._t("Layer CRS:"))
        self.lbl_output_crs_label.setText(self._t("Output CRS:"))
        self.lbl_output_crs.setText(
            self._t("WGS84 (EPSG:4326) — Required by EUDR")
        )

        # Field mapping labels
        field_labels = {
            "ProductionPlace": self._t("Production Place:"),
            "Country": self._t("Country of Production:"),
            "PlotID": self._t("Plot ID:"),
            "Area_ha": self._t("Area (ha):"),
            "Latitude": self._t("Latitude:"),
            "Longitude": self._t("Longitude:"),
            "ProductDescription": self._t("Product Description:"),
            "HSCode": self._t("HS Code:"),
            "OperatorName": self._t("Operator Name:"),
            "ProductionDate": self._t("Date of Production:"),
        }
        for key, label_text in field_labels.items():
            lbl = getattr(self, f"_lbl_{key}", None)
            if lbl:
                lbl.setText(label_text)

        # Export mode combo
        self.lbl_export_mode.setText(self._t("Export Mode:"))
        self.cbo_export_mode.blockSignals(True)
        self.cbo_export_mode.clear()
        is_vi = self.lang == 'vi'
        self.cbo_export_mode.addItem(
            "EUDR chuẩn (≤4ha→Điểm, >4ha→Polygon)" if is_vi
            else "EUDR Standard (≤4ha→Point, >4ha→Polygon)",
            MODE_EUDR_MIXED)
        self.cbo_export_mode.addItem(
            "Tất cả → Điểm (Point on Surface)" if is_vi
            else "All → Point on Surface",
            MODE_ALL_POINTS)
        self.cbo_export_mode.addItem(
            "Tất cả → Polygon + Lat/Lon" if is_vi
            else "All → Polygon + Lat/Lon",
            MODE_ALL_POLYGONS)
        self.cbo_export_mode.addItem(
            "Chỉ lô ≤4ha → Điểm" if is_vi
            else "Only ≤4ha → Point",
            MODE_POINT_UNDER_4)
        self.cbo_export_mode.addItem(
            "Chỉ lô >4ha → Polygon" if is_vi
            else "Only >4ha → Polygon",
            MODE_POLY_OVER_4)
        self.cbo_export_mode.blockSignals(False)

        # Settings labels
        self.lbl_precision.setText(
            self._t("Coordinate Precision (decimals):")
        )
        self.lbl_threshold.setText(self._t("Area Threshold (ha):"))
        self.chk_validate.setText(
            self._t("Validate geometries before export")
        )
        self.chk_auto_area.setText(
            self._t("Calculate area from geometry")
        )

        # Statistics labels
        threshold = self.spn_threshold.value()
        self.lbl_st_total.setText(self._t("Total features:"))
        self.lbl_st_point.setText(
            self._t("Point (≤ {threshold} ha):").format(threshold=threshold)
        )
        self.lbl_st_poly.setText(
            self._t("Polygon (> {threshold} ha):").format(threshold=threshold)
        )
        self.lbl_st_invalid.setText(self._t("Invalid geometries:"))

        # Buttons
        self.btn_preview.setText("📊 " + self._t("Preview Statistics"))
        self.btn_export.setText("🚀 " + self._t("Export GeoJSON"))
        self.btn_close.setText(self._t("Close"))

        # Guide and Author
        self.txt_guide.setHtml(get_guide(self.lang))
        self._update_author_html()

    def _update_author_html(self):
        """Set author profile HTML."""
        self.lbl_author.setText("""
        <div style='font-family:Arial;text-align:center;color:#333'>
        <div style='background:#f4f4f4;padding:20px;border-radius:10px'>
        <h1 style='color:#1B5E20;margin-bottom:5px;'>Lộc Vũ Trung</h1>
        <p style='font-size:14px;font-weight:bold;color:#444;margin-top:0;'>
        Chuyên gia FSC, Kỹ thuật lâm sinh, và Chuyển đổi số</p>
        <hr style='border:0;height:1px;background:#ddd;width:80%'>
        <div style='text-align:left;display:inline-block;width:80%;
        font-size:13px;line-height:1.8;margin-top:10px'>
        <b>📱 Zalo:</b> 0913 191 178<br>
        <b>🌐 Website:</b> <a href='https://locvutrung.lvtcenter.it.com'>locvutrung.lvtcenter.it.com</a><br>
        <b>🎬 YouTube:</b> <a href='https://youtube.com/@locvutrung'>youtube.com/@locvutrung</a><br>
        </div>
        <div style='margin-top:15px;background:#fff;padding:12px;
        border-radius:5px;border-left:5px solid #1B5E20;text-align:left;
        font-size:13px;line-height:1.8;box-shadow:0 2px 4px rgba(0,0,0,0.1)'>
        <b>Phạm vi chuyên môn:</b><br>
        • Hệ thống chứng chỉ rừng FSC/CoC<br>
        • Quy định chống phá rừng châu Âu (EUDR)<br>
        • Ứng dụng Webapp / Appsheet<br>
        • Hệ thống thông tin địa lý QGIS / Quản lý DATA<br>
        • Kỹ thuật Lâm sinh
        </div></div></div>
        """)

    # ------------------------------------------------------------------
    # Layer / Field Handling
    # ------------------------------------------------------------------

    def _refresh_layers(self):
        """Populate the layer combo box with vector layers."""
        self.cbo_layer.blockSignals(True)
        self.cbo_layer.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                self.cbo_layer.addItem(layer.name(), layer.id())
        self.cbo_layer.blockSignals(False)
        if self.cbo_layer.count() > 0:
            self._on_layer_changed()

    def refresh_layers(self):
        """Public method called by lvt_plugin before showing."""
        self._refresh_layers()

    def _get_selected_layer(self):
        """Return the currently selected QgsVectorLayer or None."""
        layer_id = self.cbo_layer.currentData()
        if layer_id:
            return QgsProject.instance().mapLayer(layer_id)
        return None

    def _on_layer_changed(self):
        """Update layer info and field combos when layer selection changes."""
        layer = self._get_selected_layer()
        if not layer:
            self.lbl_geom_type.setText("—")
            self.lbl_feat_count.setText("—")
            self.lbl_layer_crs.setText("—")
            return

        # Geometry type
        geom_type = QgsWkbTypes.displayString(layer.wkbType())
        self.lbl_geom_type.setText(geom_type)

        # Feature count
        self.lbl_feat_count.setText(str(layer.featureCount()))

        # CRS
        crs = layer.crs()
        crs_text = f"{crs.authid()} — {crs.description()}"
        if crs.authid() == "EPSG:4326":
            self.lbl_layer_crs.setText(crs_text)
            self.lbl_layer_crs.setStyleSheet("color: #1B5E20;")
        else:
            self.lbl_layer_crs.setText(
                crs_text + " → will transform"
            )
            self.lbl_layer_crs.setStyleSheet("color: #E65100;")

        # Update field combos
        field_names = [f.name() for f in layer.fields()]
        manual_text = self._t("-- Manual value --")
        empty_text = self._t("-- Leave empty --")

        for key, cbo in self._field_combos.items():
            cbo.blockSignals(True)
            cbo.clear()

            if key == "Area_ha":
                cbo.addItem(self._t("(auto-calculated from geometry)"),
                            "__auto__")
            elif key == "Latitude":
                cbo.addItem(self._t("(auto — Point on Surface Y)"),
                            "__auto__")
            elif key == "Longitude":
                cbo.addItem(self._t("(auto — Point on Surface X)"),
                            "__auto__")
            else:
                cbo.addItem(empty_text, "")

            for fname in field_names:
                cbo.addItem(fname, fname)

            cbo.addItem(manual_text, "__manual__")

            # Auto-match: try to find a field that matches the EUDR key
            self._auto_match_field(key, cbo, field_names)

            cbo.blockSignals(False)
            self._on_combo_changed(key)

    def _auto_match_field(self, eudr_key, cbo, field_names):
        """Try to auto-match a source field to an EUDR key."""
        # Simple heuristic matching
        hints = {
            "ProductionPlace": ["ten_lo", "name", "place", "location",
                                "noi_sx", "production"],
            "Country": ["country", "quoc_gia", "nation"],
            "PlotID": ["ma_lo", "plot_id", "id", "fid", "ma_thua"],
            "ProductDescription": ["product", "san_pham", "description",
                                   "mo_ta"],
            "HSCode": ["hs_code", "hscode", "ma_hs"],
            "OperatorName": ["operator", "company", "doanh_nghiep",
                             "ten_dn"],
            "ProductionDate": ["date", "ngay", "ngay_sx",
                               "production_date"],
        }

        keywords = hints.get(eudr_key, [])
        for fname in field_names:
            fname_lower = fname.lower()
            for hint in keywords:
                if hint in fname_lower:
                    idx = cbo.findData(fname)
                    if idx >= 0:
                        cbo.setCurrentIndex(idx)
                        return

    def _on_combo_changed(self, key):
        """Enable/disable manual text input based on combo selection."""
        cbo = self._field_combos.get(key)
        txt = self._manual_edits.get(key)
        if cbo and txt:
            is_manual = (cbo.currentData() == "__manual__")
            txt.setEnabled(is_manual)
            if is_manual:
                txt.setFocus()

    # ------------------------------------------------------------------
    # Field Mapping Builder
    # ------------------------------------------------------------------

    def _build_field_mapping(self):
        """Build field_mapping dict from current UI state."""
        mapping = {}
        for key, cbo in self._field_combos.items():
            data = cbo.currentData()
            if data == "__manual__":
                # Use static value from text input
                txt = self._manual_edits[key]
                val = txt.text().strip()
                if val:
                    mapping[key] = f"__static__:{val}"
            elif data == "__auto__":
                mapping[key] = "__auto__"
            elif data:
                mapping[key] = data
        return mapping

    # ------------------------------------------------------------------
    # Preview Statistics
    # ------------------------------------------------------------------

    def _preview_statistics(self):
        """Run preview statistics on the selected layer."""
        layer = self._get_selected_layer()
        if not layer:
            QMessageBox.warning(
                self, "LVT",
                self._t("No vector layer selected.")
            )
            return

        if layer.featureCount() == 0:
            QMessageBox.warning(
                self, "LVT",
                self._t("Selected layer has no features.")
            )
            return

        mapping = self._build_field_mapping()
        area_field = None
        if not self.chk_auto_area.isChecked():
            area_data = self._field_combos["Area_ha"].currentData()
            if area_data and area_data not in ("__auto__", "__manual__", ""):
                area_field = area_data

        builder = EudrGeoJsonBuilder(
            layer=layer,
            field_mapping=mapping,
            area_threshold_ha=self.spn_threshold.value(),
            precision=self.spn_precision.value(),
            area_field=area_field,
            validate_geometries=self.chk_validate.isChecked(),
            export_mode=self.cbo_export_mode.currentData() or MODE_EUDR_MIXED,
        )

        result = builder.preview_statistics()
        threshold = self.spn_threshold.value()

        self.lbl_stat_total.setText(str(result.total_features))
        self.lbl_stat_point.setText(str(result.point_count))
        self.lbl_stat_poly.setText(str(result.polygon_count))

        if result.invalid_count > 0:
            self.lbl_stat_invalid.setText(
                f"<span style='color:red;font-weight:bold;'>"
                f"{result.invalid_count}</span>"
            )
        else:
            self.lbl_stat_invalid.setText(
                f"<span style='color:#1B5E20;'>0 ✓</span>"
            )

        # Update threshold labels
        self.lbl_st_point.setText(
            self._t("Point (≤ {threshold} ha):").format(
                threshold=threshold)
        )
        self.lbl_st_poly.setText(
            self._t("Polygon (> {threshold} ha):").format(
                threshold=threshold)
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_geojson(self):
        """Export to EUDR-compliant GeoJSON file."""
        layer = self._get_selected_layer()
        if not layer:
            QMessageBox.warning(
                self, "LVT",
                self._t("No vector layer selected.")
            )
            return

        if layer.featureCount() == 0:
            QMessageBox.warning(
                self, "LVT",
                self._t("Selected layer has no features.")
            )
            return

        # Ask for output path
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            self._t("Save GeoJSON File"),
            "",
            self._t("GeoJSON Files (*.geojson)"),
        )
        if not out_path:
            return

        mapping = self._build_field_mapping()
        area_field = None
        if not self.chk_auto_area.isChecked():
            area_data = self._field_combos["Area_ha"].currentData()
            if area_data and area_data not in ("__auto__", "__manual__", ""):
                area_field = area_data

        builder = EudrGeoJsonBuilder(
            layer=layer,
            field_mapping=mapping,
            area_threshold_ha=self.spn_threshold.value(),
            precision=self.spn_precision.value(),
            area_field=area_field,
            validate_geometries=self.chk_validate.isChecked(),
            export_mode=self.cbo_export_mode.currentData() or MODE_EUDR_MIXED,
        )

        success, message, result = builder.build(out_path)

        if success:
            msg = self._t(
                "Export completed successfully!\n\n"
                "File: {path}\nFeatures: {count}\n"
                "Points: {points}\nPolygons: {polygons}"
            ).format(
                path=message,
                count=result.valid_count,
                points=result.point_count,
                polygons=result.polygon_count,
            )
            QMessageBox.information(self, "LVT", msg)

            # Update statistics panel
            self.lbl_stat_total.setText(str(result.total_features))
            self.lbl_stat_point.setText(str(result.point_count))
            self.lbl_stat_poly.setText(str(result.polygon_count))
            self.lbl_stat_invalid.setText(str(result.invalid_count))
        else:
            QMessageBox.critical(
                self, "LVT",
                self._t("Export failed:\n{error}").format(error=message),
            )
