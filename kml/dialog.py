import os
import re
import json
from qgis.PyQt import uic, QtCore, QtGui
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
    QLabel, QComboBox, QLineEdit, QPushButton, QSpinBox, 
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QColorDialog, QGroupBox, QTextEdit,
    QSlider, QRadioButton, QButtonGroup, QScrollArea, QFrame
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QPoint
from qgis.PyQt.QtGui import QIcon, QColor, QPainter, QPen, QBrush, QPixmap, QPolygon
from qgis.core import QgsProject, QgsVectorLayer

from .kml_i18n import tr, get_help
from .config_manager import ConfigManager
from .kml_builder import KmlBuilder
from .kml_to_shp import KmlToShpConverter
from .html_template import HtmlTemplateBuilder

class LvtKmlViewDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.bg_img = os.path.join(self.plugin_dir, "google_maps_satellite_bg.png")
        self.config_manager = ConfigManager()
        self.lang = 'vi'
        
        self.resize(950, 750) 
        self._setup_ui()
        self._load_current_layers()
        self._refresh_ui_text()
        self._connect_live_preview()
        
        self.btn_close.clicked.connect(self.close)
        self.btn_save_cfg.clicked.connect(self._save_config)
        self.btn_load_cfg.clicked.connect(self._load_config)
        self.btn_reset.clicked.connect(self._reset_config)
        
        QtCore.QTimer.singleShot(1000, self._on_layer_changed)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        left_widget = QWidget(); left_layout = QVBoxLayout(left_widget); scroll.setWidget(left_widget)
        main_layout.addWidget(scroll, 6)

        top_ly = QHBoxLayout()
        self.btn_lang = QPushButton(); self.btn_lang.setFixedWidth(100); self.btn_lang.clicked.connect(self._toggle_language)
        top_ly.addWidget(self.btn_lang); top_ly.addStretch(); left_layout.addLayout(top_ly)

        self.tabs = QTabWidget(); left_layout.addWidget(self.tabs)
        self.tab_shp2kml = QWidget(); self._setup_tab_shp2kml(); self.tabs.addTab(self.tab_shp2kml, "SHP → KML")
        self.tab_kml2shp = QWidget(); self._setup_tab_kml2shp(); self.tabs.addTab(self.tab_kml2shp, "KML → SHP")
        self.tab_guide = QWidget(); self._setup_tab_guide(); self.tabs.addTab(self.tab_guide, "")
        self.tab_author = QWidget(); self._setup_tab_author(); self.tabs.addTab(self.tab_author, "")

        btn_layout = QHBoxLayout()
        self.btn_save_cfg = QPushButton()
        self.btn_load_cfg = QPushButton()
        self.btn_close = QPushButton()
        btn_layout.addWidget(self.btn_save_cfg); btn_layout.addWidget(self.btn_load_cfg); btn_layout.addStretch(); btn_layout.addWidget(self.btn_close)
        left_layout.addLayout(btn_layout)

        right_widget = QGroupBox("LIVE PREVIEW"); right_layout = QVBoxLayout(right_widget); main_layout.addWidget(right_widget, 4)
        right_layout.addWidget(QLabel("<b>Polygon Contrast Preview:</b>"))
        self.poly_preview = QFrame(); self.poly_preview.setMinimumHeight(180); self.poly_preview.setFrameStyle(QFrame.StyledPanel)
        self.poly_preview.setStyleSheet(f"background-image: url({self.bg_img.replace('\\', '/')}); background-position: center;")
        self.poly_preview.paintEvent = self._paint_poly_preview; right_layout.addWidget(self.poly_preview)
        right_layout.addWidget(QLabel("<b>Popup Preview:</b>"))
        self.html_preview = QTextEdit(); self.html_preview.setReadOnly(True); right_layout.addWidget(self.html_preview)
        self.btn_export_big = QPushButton()
        self.btn_export_big.setMinimumHeight(50); self.btn_export_big.setStyleSheet("background-color: #1B5E20; color: white; font-weight: bold; border-radius: 5px")
        self.btn_export_big.clicked.connect(self._export); right_layout.addWidget(self.btn_export_big)

    def _setup_tab_shp2kml(self):
        layout = QVBoxLayout(self.tab_shp2kml)
        self.gp_io = QGroupBox(); io_ly = QVBoxLayout()
        r2 = QHBoxLayout(); self.lbl_sel_layer = QLabel(); r2.addWidget(self.lbl_sel_layer); self.cbo_layers = QComboBox(); r2.addWidget(self.cbo_layers, 1)
        self.btn_reset = QPushButton(); r2.addWidget(self.btn_reset)
        io_ly.addLayout(r2)
        self.gp_io.setLayout(io_ly); layout.addWidget(self.gp_io)
        
        self.gp_name = QGroupBox(); name_main_ly = QVBoxLayout()
        n_ly = QHBoxLayout()
        self.cbo_name1 = QComboBox(); self.txt_sep = QLineEdit(" - "); self.cbo_name2 = QComboBox()
        self.spn_name_size = QSpinBox(); self.spn_name_size.setRange(8, 72); self.spn_name_size.setValue(12)
        self.btn_name_color = QPushButton("#000000")
        self.btn_name_color.setStyleSheet("background-color: #000000; color: white;")
        
        n_ly.addWidget(QLabel("F1:")); n_ly.addWidget(self.cbo_name1, 1)
        n_ly.addWidget(QLabel("Sep:")); n_ly.addWidget(self.txt_sep)
        n_ly.addWidget(QLabel("F2:")); n_ly.addWidget(self.cbo_name2, 1)
        self.lbl_name_size = QLabel(); n_ly.addWidget(self.lbl_name_size); n_ly.addWidget(self.spn_name_size)
        self.lbl_name_color = QLabel(); n_ly.addWidget(self.lbl_name_color); n_ly.addWidget(self.btn_name_color)
        
        self.lbl_name_preview = QLabel("<b>Preview:</b> <i>Unnamed</i>")
        self.lbl_name_preview.setStyleSheet("color: #1B5E20;")
        
        name_main_ly.addLayout(n_ly)
        name_main_ly.addWidget(self.lbl_name_preview)
        
        self.gp_name.setLayout(name_main_ly); layout.addWidget(self.gp_name)
        
        self.gp_desc = QGroupBox(); d_ly = QVBoxLayout()
        btn_ly_desc = QHBoxLayout()
        self.btn_check_all = QPushButton()
        self.btn_uncheck_all = QPushButton()
        self.btn_check_all.clicked.connect(self._check_all_fields)
        self.btn_uncheck_all.clicked.connect(self._uncheck_all_fields)
        btn_ly_desc.addWidget(self.btn_check_all)
        btn_ly_desc.addWidget(self.btn_uncheck_all)
        btn_ly_desc.addStretch()
        d_ly.addLayout(btn_ly_desc)
        
        self.tbl_fields = QTableWidget(0, 4); self.tbl_fields.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); d_ly.addWidget(self.tbl_fields)
        self.gp_desc.setLayout(d_ly); layout.addWidget(self.gp_desc)
        
        self.gp_poly = QGroupBox(); p_ly = QHBoxLayout()
        self.btn_border = QPushButton("#FF0000"); self.spn_width = QSpinBox(); self.btn_fill = QPushButton("#00FF00"); self.sld_op = QSlider(Qt.Horizontal)
        self.sld_op.setRange(0, 100); self.sld_op.setValue(50)
        self.btn_border.setStyleSheet("background-color: #FF0000"); self.btn_fill.setStyleSheet("background-color: #00FF00")
        self.lbl_border = QLabel(); self.lbl_width = QLabel(); self.lbl_fill = QLabel(); self.lbl_op = QLabel()
        p_ly.addWidget(self.lbl_border); p_ly.addWidget(self.btn_border); p_ly.addWidget(self.lbl_width); p_ly.addWidget(self.spn_width)
        p_ly.addWidget(self.lbl_fill); p_ly.addWidget(self.btn_fill); p_ly.addWidget(self.lbl_op); p_ly.addWidget(self.sld_op)
        self.gp_poly.setLayout(p_ly); layout.addWidget(self.gp_poly)
        
        self.gp_hl = QGroupBox(); hl_ly = QVBoxLayout()
        r3 = QHBoxLayout(); self.txt_h_title = QLineEdit("Thông tin"); self.btn_h_bg = QPushButton("#1B5E20"); self.btn_h_bg.setStyleSheet("background-color: #1B5E20")
        self.lbl_header = QLabel(); r3.addWidget(self.lbl_header); r3.addWidget(self.txt_h_title, 1); r3.addWidget(self.btn_h_bg)
        hl_ly.addLayout(r3); self.chk_row_hl = QCheckBox(); hl_ly.addWidget(self.chk_row_hl)
        self.tbl_rules = QTableWidget(0, 5); self.tbl_rules.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_rules.setMaximumHeight(130)
        hl_ly.addWidget(self.tbl_rules)
        r4 = QHBoxLayout(); btn_add = QPushButton("+ Add Rule"); btn_del = QPushButton("- Del"); btn_add.clicked.connect(self._add_rule); btn_del.clicked.connect(self._del_rule); r4.addWidget(btn_add); r4.addWidget(btn_del); r4.addStretch()
        hl_ly.addLayout(r4); self.gp_hl.setLayout(hl_ly); layout.addWidget(self.gp_hl)

    def _setup_tab_author(self):
        ly = QVBoxLayout(self.tab_author)
        self.author = QLabel()
        self.author.setOpenExternalLinks(True)
        self.author.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.author.setWordWrap(True)
        ly.addWidget(self.author)
        ly.addStretch()

    def _setup_tab_guide(self): 
        ly = QVBoxLayout(self.tab_guide); self.guide = QTextEdit(); self.guide.setReadOnly(True); ly.addWidget(self.guide)

    def _setup_tab_kml2shp(self):
        ly = QVBoxLayout(self.tab_kml2shp)
        self.lbl_kml_src = QLabel()
        ly.addWidget(self.lbl_kml_src)
        
        row_kml = QHBoxLayout()
        self.txt_kml_in = QLineEdit()
        self.btn_browse_kml = QPushButton("...")
        self.btn_browse_kml.setFixedWidth(40)
        self.btn_browse_kml.clicked.connect(self._browse_kml)
        row_kml.addWidget(self.txt_kml_in)
        row_kml.addWidget(self.btn_browse_kml)
        ly.addLayout(row_kml)
        
        self.lbl_crs = QLabel()
        ly.addWidget(self.lbl_crs)
        self.txt_crs = QLineEdit("EPSG:4326")
        ly.addWidget(self.txt_crs)
        
        self.btn_extract = QPushButton()
        self.btn_extract.clicked.connect(self._convert_kml)
        ly.addWidget(self.btn_extract)
        ly.addStretch()

    def _refresh_ui_text(self):
        self.setWindowTitle("LVT4U KML view")
        self.btn_lang.setText("🌐 " + ("English" if self.lang == 'vi' else "Tiếng Việt"))
        is_vi = self.lang == 'vi'
        
        self.gp_io.setTitle("1. Chọn lớp dữ liệu (Input)" if is_vi else "1. Input / Output")
        self.lbl_sel_layer.setText("Lớp bản đồ:" if is_vi else "Select Layer:")
        self.btn_reset.setText("Reset Cấu Hình" if is_vi else "Reset Config")
        
        self.gp_name.setTitle("2. Thiết lập Tên (Name)" if is_vi else "2. Name Settings")
        self.lbl_name_size.setText("Cỡ chữ:" if is_vi else "Size:")
        self.lbl_name_color.setText("Màu:" if is_vi else "Color:")
        
        self.gp_desc.setTitle("3. Thiết lập Popup (Fields)" if is_vi else "3. Popup Info")
        self.btn_check_all.setText("Chọn tất cả" if is_vi else "Check All")
        self.btn_uncheck_all.setText("Bỏ chọn tất cả" if is_vi else "Uncheck All")
        self.tbl_fields.setHorizontalHeaderLabels(["√", "Trường" if is_vi else "Field", "Bí danh" if is_vi else "Alias", "Đơn vị" if is_vi else "Unit"])
        
        self.gp_poly.setTitle("4. Giao diện Vùng (Style)" if is_vi else "4. Style")
        self.lbl_border.setText("Viền:" if is_vi else "Border:")
        self.lbl_width.setText("Độ dày:" if is_vi else "Width:")
        self.lbl_fill.setText("Nền:" if is_vi else "Fill:")
        self.lbl_op.setText("Độ mờ:" if is_vi else "Opacity:")
        
        self.gp_hl.setTitle("5. Định dạng có điều kiện" if is_vi else "5. Conditions")
        self.lbl_header.setText("Tiêu đề:" if is_vi else "Header:")
        self.chk_row_hl.setText("Bật tô màu dòng" if is_vi else "Enable Highlighting")
        
        self.btn_save_cfg.setText("Lưu cấu hình" if is_vi else "Save Config")
        self.btn_load_cfg.setText("Mở cấu hình" if is_vi else "Load Config")
        self.btn_close.setText("Đóng" if is_vi else "Close")
        self.btn_export_big.setText("🚀 XUẤT KML / KMZ" if is_vi else "🚀 EXPORT KML / KMZ")
        
        self.lbl_kml_src.setText("Đường dẫn KML:" if is_vi else "KML Source:")
        self.lbl_crs.setText("Hệ tọa độ:" if is_vi else "Target CRS:")
        self.btn_extract.setText("🔄 CHUYỂN ĐỔI SHP" if is_vi else "🔄 EXTRACT SHP")
        
        self.tabs.setTabText(0, "SHP → KML")
        self.tabs.setTabText(1, "KML → SHP")
        self.tabs.setTabText(2, "Hướng dẫn" if is_vi else "Guide")
        self.tabs.setTabText(3, "Tác giả" if is_vi else "Author")

        author_html = f"""<div style='font-family:Arial;text-align:center;color:#333'><div style='background:#f4f4f4;padding:20px;border-radius:10px'><h1 style='color:#1B5E20;margin-bottom:5px;'>Lộc Vũ Trung</h1><p style='font-size:18px;font-weight:bold;color:#444;margin-top:0;'>Chuyên gia FSC, Kỹ thuật lâm sinh, và Chuyển đổi số</p><hr style='border: 0; height: 1px; background: #ddd; width: 80%;'><div style='text-align:left;display:inline-block;width:80%;font-size:15px;line-height:1.6;margin-top:10px;'><b>📱 Zalo:</b> 0913 191 178<br><b>🌐 Website:</b> <a href='http://locvutrung.lvtcenter.it.com' style='color:#1B5E20;text-decoration:none'>locvutrung.lvtcenter.it.com</a><br><b>🎬 YouTube:</b> <a href='https://youtube.com/@locvutrung' style='color:#1B5E20;text-decoration:none'>youtube.com/@locvutrung</a><br></div><div style='margin-top:20px;background:#fff;padding:15px;border-radius:5px;border-left:5px solid #1B5E20;text-align:left;font-size:15px;line-height:1.8;box-shadow: 0 2px 4px rgba(0,0,0,0.1);'><b>Phạm vi chuyên môn:</b><br>• Hệ thống chứng chỉ rừng FSC/CoC<br>• Quy định chống phá rừng châu Âu (EUDR)<br>• Ứng dụng Webapp / Appsheet<br>• Hệ thống thông tin địa lý QGIS / Quản lý DATA<br>• Kỹ thuật Lâm sinh</div></div></div>"""
        self.author.setText(author_html)
        self.guide.setHtml(get_help(self.lang))

    def _load_current_layers(self):
        self.cbo_layers.blockSignals(True)
        self.cbo_layers.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer): self.cbo_layers.addItem(layer.name())
        self.cbo_layers.blockSignals(False)

    def _connect_live_preview(self):
        self.cbo_layers.currentIndexChanged.connect(self._on_layer_changed)
        for w in [self.cbo_name1, self.cbo_name2, self.txt_sep, self.sld_op, self.spn_width, self.txt_h_title, self.chk_row_hl, self.spn_name_size]:
            if hasattr(w, 'textChanged'): w.textChanged.connect(self._trigger_refresh)
            if hasattr(w, 'valueChanged'): w.valueChanged.connect(self._trigger_refresh)
            if hasattr(w, 'toggled'): w.toggled.connect(self._trigger_refresh)
            if hasattr(w, 'currentIndexChanged'): w.currentIndexChanged.connect(self._trigger_refresh)
        self.btn_border.clicked.connect(lambda: (self._pick_color(self.btn_border), self._trigger_refresh()))
        self.btn_fill.clicked.connect(lambda: (self._pick_color(self.btn_fill), self._trigger_refresh()))
        self.btn_h_bg.clicked.connect(lambda: (self._pick_color(self.btn_h_bg), self._trigger_refresh()))
        self.btn_name_color.clicked.connect(lambda: (self._pick_color(self.btn_name_color), self._trigger_refresh()))
        self.tbl_fields.itemChanged.connect(self._trigger_refresh); self.tbl_rules.itemChanged.connect(self._trigger_refresh)

    def _trigger_refresh(self):
        self.poly_preview.update()
        try: self._update_popup_preview()
        except: pass

    def _paint_poly_preview(self, event):
        painter = QPainter(self.poly_preview); painter.setRenderHint(QPainter.Antialiasing)
        b_c = QColor(self.btn_border.text()); f_c = QColor(self.btn_fill.text()); w = self.spn_width.value()
        f_c.setAlpha(int(self.sld_op.value() * 2.55)); painter.setPen(QPen(b_c, w)); painter.setBrush(QBrush(f_c))
        pts = [QPoint(175, 40), QPoint(300, 100), QPoint(175, 160), QPoint(50, 100)]; painter.drawPolygon(QPolygon(pts))
        try:
            cfg = self._get_current_config()
            nm = cfg.get('name_fields', {})
            c_nm = nm.get('font_color', '#000000')
            sz = nm.get('font_size', 12)
            name_val = "Sample"
            layers = QgsProject.instance().mapLayersByName(self.cbo_layers.currentText())
            if layers:
                feat = next(layers[0].getFeatures(), None)
                if feat:
                    f1, f2 = nm.get('field1', ''), nm.get('field2', '')
                    sep = nm.get('separator', ' - ')
                    fnames = [f.name() for f in feat.fields()]
                    v1 = str(feat[f1]) if f1 in fnames and feat[f1] is not None else ''
                    v2 = str(feat[f2]) if f2 in fnames and feat[f2] is not None else ''
                    if v1 and v2: name_val = f"{v1}{sep}{v2}"
                    else: name_val = v1 or v2 or 'Unnamed'
            font = painter.font(); font.setPointSize(sz); painter.setFont(font)
            painter.setPen(QColor(c_nm))
            painter.drawText(QRect(50, 40, 250, 120), Qt.AlignCenter, name_val)
        except Exception: pass

    def _on_layer_changed(self):
        layers = QgsProject.instance().mapLayersByName(self.cbo_layers.currentText())
        if layers: self._update_fields(layers[0]); self._trigger_refresh()

    def _update_fields(self, layer):
        self.tbl_fields.blockSignals(True); fnames = [f.name() for f in layer.fields()]
        self.cbo_name1.clear(); self.cbo_name1.addItems(fnames); self.cbo_name2.clear(); self.cbo_name2.addItems(fnames)
        self.tbl_fields.setRowCount(0)
        for i, name in enumerate(fnames):
            self.tbl_fields.insertRow(i); chk = QCheckBox(); chk.setChecked(True); self.tbl_fields.setCellWidget(i, 0, chk)
            self.tbl_fields.setItem(i, 1, QTableWidgetItem(name)); self.tbl_fields.setItem(i, 2, QTableWidgetItem(name)); self.tbl_fields.setItem(i, 3, QTableWidgetItem(""))
        self.tbl_fields.blockSignals(False); self._trigger_refresh()

    def _update_popup_preview(self):
        layers = QgsProject.instance().mapLayersByName(self.cbo_layers.currentText())
        if layers:
            feat = next(layers[0].getFeatures(), None)
            if feat:
                cfg = self._get_current_config()
                if cfg: 
                    html = HtmlTemplateBuilder(cfg).build({f.name(): feat[f.name()] for f in feat.fields()})
                    self.html_preview.setHtml(f"<div align='center'>{html}</div>")
                    
                    # Name Preview
                    nm = cfg.get('name_fields', {})
                    f1, f2 = nm.get('field1', ''), nm.get('field2', '')
                    sep = nm.get('separator', ' - ')
                    fnames = [f.name() for f in feat.fields()]
                    v1 = str(feat[f1]) if f1 in fnames and feat[f1] is not None else ''
                    v2 = str(feat[f2]) if f2 in fnames and feat[f2] is not None else ''
                    if v1 and v2:
                        name_val = f"{v1}{sep}{v2}"
                    else:
                        name_val = v1 or v2 or 'Unnamed'
                        
                    c_nm = nm.get('font_color', '#000000')
                    sz = nm.get('font_size', 12)
                    self.lbl_name_preview.setText(f"<b>Preview:</b> <span style='color:{c_nm}; font-size:{sz}px'>{name_val}</span>")

    def _get_current_config(self):
        rules = []
        for i in range(self.tbl_rules.rowCount()):
            rules.append({'field': self.tbl_rules.cellWidget(i,0).currentText() if self.tbl_rules.cellWidget(i,0) else "", 'operator': self.tbl_rules.cellWidget(i,1).currentText() if self.tbl_rules.cellWidget(i,1) else "=", 'value': self.tbl_rules.item(i,2).text() if self.tbl_rules.item(i,2) else "", 'text_color': self.tbl_rules.cellWidget(i,3).text() if self.tbl_rules.cellWidget(i,3) else "#000", 'bg_color': self.tbl_rules.cellWidget(i,4).text() if self.tbl_rules.cellWidget(i,4) else "#fff", 'bold': True, 'italic': False})
        df = []
        for i in range(self.tbl_fields.rowCount()):
            chk = self.tbl_fields.cellWidget(i,0)
            if chk and chk.isChecked():
                f_item = self.tbl_fields.item(i,1); a_item = self.tbl_fields.item(i,2); s_item = self.tbl_fields.item(i,3)
                if f_item and a_item: df.append({'field': f_item.text(), 'alias': a_item.text(), 'suffix': s_item.text() if s_item else "", 'order': i})
        return {
            'name_fields': {'field1': self.cbo_name1.currentText(), 'field2': self.cbo_name2.currentText(), 'separator': self.txt_sep.text(), 'font_size': self.spn_name_size.value(), 'font_color': self.btn_name_color.text()}, 
            'description_fields': df, 
            'polygon_style': {'border_color': self.btn_border.text(), 'border_width': self.spn_width.value(), 'fill_color': self.btn_fill.text(), 'fill_opacity': self.sld_op.value()}, 
            'header': {'title': self.txt_h_title.text(), 'bg_color': self.btn_h_bg.text(), 'text_color': "#FFFFFF", 'bold': True, 'font_size': 14}, 
            'row_highlights': {'enabled': self.chk_row_hl.isChecked(), 'rules': rules}
        }

    def _apply_config(self, cfg):
        nm = cfg.get('name_fields', {})
        idx1 = self.cbo_name1.findText(nm.get('field1', '')); 
        if idx1 >= 0: self.cbo_name1.setCurrentIndex(idx1)
        idx2 = self.cbo_name2.findText(nm.get('field2', '')); 
        if idx2 >= 0: self.cbo_name2.setCurrentIndex(idx2)
        self.txt_sep.setText(nm.get('separator', ' - '))
        self.spn_name_size.setValue(nm.get('font_size', 12))
        c_nm = nm.get('font_color', '#000000')
        self.btn_name_color.setText(c_nm)
        self.btn_name_color.setStyleSheet(f"background-color: {c_nm}; color: {'white' if c_nm.lower()=='#000000' else 'black'};")
        
        ps = cfg.get('polygon_style', {})
        self.spn_width.setValue(ps.get('border_width', 2))
        self.sld_op.setValue(ps.get('fill_opacity', 50))
        bc = ps.get('border_color', '#FF0000'); self.btn_border.setText(bc); self.btn_border.setStyleSheet(f"background-color: {bc}")
        fc = ps.get('fill_color', '#00FF00'); self.btn_fill.setText(fc); self.btn_fill.setStyleSheet(f"background-color: {fc}")

        hd = cfg.get('header', {})
        self.txt_h_title.setText(hd.get('title', 'Thông tin'))
        hbc = hd.get('bg_color', '#1B5E20'); self.btn_h_bg.setText(hbc); self.btn_h_bg.setStyleSheet(f"background-color: {hbc}")

        rh = cfg.get('row_highlights', {})
        self.chk_row_hl.setChecked(rh.get('enabled', False))
        rules = rh.get('rules', [])
        self.tbl_rules.setRowCount(0)
        for rule in rules:
            self._add_rule()
            r = self.tbl_rules.rowCount() - 1
            cb = self.tbl_rules.cellWidget(r, 0); 
            if cb:
                idx = cb.findText(rule.get('field', ''))
                if idx >= 0: cb.setCurrentIndex(idx)
            cb_op = self.tbl_rules.cellWidget(r, 1); 
            if cb_op:
                idx = cb_op.findText(rule.get('operator', '='))
                if idx >= 0: cb_op.setCurrentIndex(idx)
            self.tbl_rules.item(r, 2).setText(rule.get('value', ''))
            tc = rule.get('text_color', '#000000'); btn_tc = self.tbl_rules.cellWidget(r, 3); btn_tc.setText(tc); btn_tc.setStyleSheet(f"background-color: {tc}")
            bgc = rule.get('bg_color', '#FFFFFF'); btn_bgc = self.tbl_rules.cellWidget(r, 4); btn_bgc.setText(bgc); btn_bgc.setStyleSheet(f"background-color: {bgc}")

        df = cfg.get('description_fields', [])
        df_dict = {f['field']: f for f in df}
        for i in range(self.tbl_fields.rowCount()):
            f_name = self.tbl_fields.item(i, 1).text()
            chk = self.tbl_fields.cellWidget(i, 0)
            if f_name in df_dict:
                chk.setChecked(True)
                self.tbl_fields.item(i, 2).setText(df_dict[f_name].get('alias', f_name))
                self.tbl_fields.item(i, 3).setText(df_dict[f_name].get('suffix', ''))
            else:
                chk.setChecked(False)
        self._trigger_refresh()

    def _export(self):
        layers = QgsProject.instance().mapLayersByName(self.cbo_layers.currentText())
        if layers:
            out_path, _ = QFileDialog.getSaveFileName(self, "Save KML/KMZ", "", "KML (*.kml);;KMZ (*.kmz)")
            if out_path:
                builder = KmlBuilder(self._get_current_config())
                success, msg = builder.build(layers[0], out_path, 'kmz' if out_path.lower().endswith('.kmz') else 'kml')
                if success:
                    QMessageBox.information(self, "Success", tr('msg_success', self.lang))
                else:
                    QMessageBox.warning(self, "Lỗi" if self.lang == 'vi' else "Error", f"Xuất file thất bại:\n{msg}" if self.lang == 'vi' else f"Export failed:\n{msg}")

    def _toggle_language(self): self.lang = 'en' if self.lang == 'vi' else 'vi'; self._refresh_ui_text(); self._trigger_refresh()
    def _pick_color(self, btn):
        c = QColorDialog.getColor(QColor(btn.text())); 
        if c.isValid(): btn.setText(c.name()); btn.setStyleSheet(f"background-color: {c.name()}")
    def _add_rule(self):
        r = self.tbl_rules.rowCount(); self.tbl_rules.insertRow(r)
        cb = QComboBox(); layers = QgsProject.instance().mapLayersByName(self.cbo_layers.currentText())
        if layers: cb.addItems([f.name() for f in layers[0].fields()])
        self.tbl_rules.setCellWidget(r, 0, cb); cb_op = QComboBox(); cb_op.addItems(["=", ">", "<"]); self.tbl_rules.setCellWidget(r, 1, cb_op)
        self.tbl_rules.setItem(r, 2, QTableWidgetItem("")); self.tbl_rules.setCellWidget(r, 3, QPushButton("#C62828")); self.tbl_rules.setCellWidget(r, 4, QPushButton("#FFF5F5"))
    def _del_rule(self): self.tbl_rules.removeRow(self.tbl_rules.currentRow())
    
    def _save_config(self):
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Config", "", "JSON (*.json)")
        if out_path:
            with open(out_path, 'w', encoding='utf-8') as f: json.dump(self._get_current_config(), f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Success", "Lưu cấu hình thành công!" if self.lang == 'vi' else "Configuration saved!")

    def _load_config(self):
        in_path, _ = QFileDialog.getOpenFileName(self, "Load Config", "", "JSON (*.json)")
        if in_path:
            with open(in_path, 'r', encoding='utf-8') as f: cfg = json.load(f)
            self._apply_config(cfg)
            QMessageBox.information(self, "Success", "Mở cấu hình thành công!" if self.lang == 'vi' else "Configuration loaded!")

    def _reset_config(self):
        self.txt_sep.setText(" - "); self.spn_name_size.setValue(12)
        self.btn_name_color.setText("#000000"); self.btn_name_color.setStyleSheet("background-color: #000000; color: white;")
        self.btn_border.setText("#FF0000"); self.btn_border.setStyleSheet("background-color: #FF0000")
        self.btn_fill.setText("#00FF00"); self.btn_fill.setStyleSheet("background-color: #00FF00")
        self.spn_width.setValue(2); self.sld_op.setValue(50)
        self.txt_h_title.setText("Thông tin"); self.btn_h_bg.setText("#1B5E20"); self.btn_h_bg.setStyleSheet("background-color: #1B5E20")
        self.chk_row_hl.setChecked(False); self.tbl_rules.setRowCount(0); self._on_layer_changed()
        
    def _check_all_fields(self):
        self.tbl_fields.blockSignals(True)
        for i in range(self.tbl_fields.rowCount()):
            chk = self.tbl_fields.cellWidget(i, 0)
            if chk: chk.setChecked(True)
        self.tbl_fields.blockSignals(False)
        self._trigger_refresh()

    def _uncheck_all_fields(self):
        self.tbl_fields.blockSignals(True)
        for i in range(self.tbl_fields.rowCount()):
            chk = self.tbl_fields.cellWidget(i, 0)
            if chk: chk.setChecked(False)
        self.tbl_fields.blockSignals(False)
        self._trigger_refresh()

    def _browse_kml(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn File KML/KMZ", "", "KML/KMZ Files (*.kml *.kmz)")
        if file_path:
            self.txt_kml_in.setText(file_path)

    def _convert_kml(self):
        # Implementation for KML to SHP
        kml_path = self.txt_kml_in.text()
        if not kml_path or not os.path.exists(kml_path):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn KML!" if self.lang == 'vi' else "Please select valid KML!")
            return
        out_shp, _ = QFileDialog.getSaveFileName(self, "Lưu SHP", "", "Shapefile (*.shp)")
        if out_shp:
            converter = KmlToShpConverter()
            success, msg = converter.convert(kml_path, out_shp, self.txt_crs.text())
            QMessageBox.information(self, "Success", msg)
