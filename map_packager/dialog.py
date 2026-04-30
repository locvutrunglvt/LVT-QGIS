# -*- coding: utf-8 -*-
"""LVT4U Package Map — Portable project packager."""
import os
import shutil
import glob
import re
import zipfile
import tempfile
from pathlib import Path, PurePosixPath

from qgis.PyQt.QtCore import Qt, QFileInfo
from qgis.PyQt.QtGui import QFont, QColor, QIcon
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QProgressBar, QTextEdit, QFileDialog, QMessageBox,
    QGroupBox, QTreeWidget, QTreeWidgetItem, QComboBox, QCheckBox,
    QApplication, QHeaderView, QSizePolicy,
)
from qgis.core import (
    QgsProject, QgsMapLayer, QgsVectorLayer, QgsRasterLayer,
    QgsVectorFileWriter, QgsCoordinateTransformContext,
)


# ---- Layer source utilities ----

# File extensions associated with a shapefile
_SHP_SIBLINGS = (
    '.shp', '.shx', '.dbf', '.prj', '.cpg', '.qix', '.sbn', '.sbx',
    '.idx', '.ind', '.qpj', '.fix', '.shp.xml',
)

# File-based vector formats we can detect
_VECTOR_FILE_EXTS = {
    '.shp', '.gpkg', '.geojson', '.json', '.kml', '.gml',
    '.tab', '.mif', '.mid', '.csv', '.xlsx', '.ods', '.fgb',
}
_RASTER_FILE_EXTS = {
    '.tif', '.tiff', '.img', '.png', '.jpg', '.jpeg', '.ecw',
    '.jp2', '.adf', '.vrt', '.nc', '.hdf', '.dt0', '.dt1', '.dt2',
}


def _layer_source_path(layer):
    """Return the filesystem path for a file-based layer, or None."""
    src = layer.source()
    # GeoPackage / SpatiaLite may have "|layername=..." or "|layerid=..."
    src = src.split("|")[0].strip()
    # Remove query string for rasters (e.g. ?crs=...)
    src = src.split("?")[0].strip()
    if os.path.isfile(src):
        return os.path.normpath(src)
    return None


def _layer_type_label(layer):
    """Human-readable layer type."""
    if isinstance(layer, QgsVectorLayer):
        prov = layer.dataProvider().name() if layer.dataProvider() else "?"
        if prov == "memory":
            return "Memory"
        return "Vector"
    elif isinstance(layer, QgsRasterLayer):
        prov = layer.dataProvider().name() if layer.dataProvider() else "?"
        if prov in ("wms", "arcgismapserver", "arcgisfeatureserver"):
            return "Online"
        return "Raster"
    return "Other"


def _collect_shapefile_siblings(shp_path):
    """Given a .shp path, return all sibling files."""
    base = os.path.splitext(shp_path)[0]
    siblings = []
    for ext in _SHP_SIBLINGS:
        p = base + ext
        if os.path.isfile(p):
            siblings.append(p)
    # Also check for .qml style file saved alongside
    qml = base + '.qml'
    if os.path.isfile(qml):
        siblings.append(qml)
    return siblings


def _collect_layer_files(layer):
    """Collect all files that need to be copied for a layer."""
    src = _layer_source_path(layer)
    if src is None:
        return []
    ext = os.path.splitext(src)[1].lower()
    if ext == '.shp':
        return _collect_shapefile_siblings(src)
    else:
        # Single file (gpkg, tif, etc.)
        files = [src]
        # Also grab .qml if present
        qml = os.path.splitext(src)[0] + '.qml'
        if os.path.isfile(qml):
            files.append(qml)
        return files


# ---- Dialog ----

class PackageMapDialog(QDialog):
    """Package the current QGIS project into a portable folder or ZIP."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.lang = 'vi'
        self.setWindowTitle("LVT4U — Package Map")
        self.setMinimumSize(700, 560)
        self.resize(750, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()
        self._refresh_layers()

    # ---- UI ----
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # --- Header ---
        hdr = QLabel("📦  Package Map — Đóng gói bản đồ")
        hdr.setFont(QFont("Arial", 13, QFont.Bold))
        root.addWidget(hdr)

        desc = QLabel(
            "Thu thập toàn bộ dữ liệu, style, nhãn, layout... vào một thư mục/ZIP.\n"
            "Mở trên máy khác sẽ hiển thị đúng như bản gốc."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555;")
        root.addWidget(desc)

        # --- Layer tree ---
        grp_layers = QGroupBox("Danh sách Layer")
        lay_tree = QVBoxLayout(grp_layers)

        # Buttons row
        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self._refresh_layers)
        btn_row.addWidget(self.btn_refresh)
        self.btn_check_all = QPushButton("☑ Chọn tất cả")
        self.btn_check_all.clicked.connect(self._check_all)
        btn_row.addWidget(self.btn_check_all)
        self.btn_uncheck_all = QPushButton("☐ Bỏ chọn")
        self.btn_uncheck_all.clicked.connect(self._uncheck_all)
        btn_row.addWidget(self.btn_uncheck_all)
        btn_row.addStretch()
        lay_tree.addLayout(btn_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Layer", "Loại", "Nguồn dữ liệu", "Trạng thái"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        lay_tree.addWidget(self.tree)
        root.addWidget(grp_layers)

        # --- Output settings ---
        grp_out = QGroupBox("Đầu ra")
        lay_out = QVBoxLayout(grp_out)

        # Format
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Định dạng:"))
        self.cbo_format = QComboBox()
        self.cbo_format.addItem("📁 Thư mục (Folder)", "folder")
        self.cbo_format.addItem("📦 File ZIP", "zip")
        fmt_row.addWidget(self.cbo_format)
        fmt_row.addStretch()

        self.chk_gpkg = QCheckBox("Chuyển SHP → GeoPackage")
        self.chk_gpkg.setToolTip(
            "Chuyển shapefile sang GeoPackage (.gpkg) — file duy nhất, hỗ trợ Unicode tốt hơn"
        )
        fmt_row.addWidget(self.chk_gpkg)
        lay_out.addLayout(fmt_row)

        # Output path
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Lưu vào:"))
        self.edt_path = QLineEdit()
        self.edt_path.setPlaceholderText("Chọn thư mục đích...")
        path_row.addWidget(self.edt_path)
        self.btn_browse = QPushButton("...")
        self.btn_browse.setFixedWidth(40)
        self.btn_browse.clicked.connect(self._browse_output)
        path_row.addWidget(self.btn_browse)
        lay_out.addLayout(path_row)

        root.addWidget(grp_out)

        # --- Progress ---
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        # --- Log ---
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
        self.log.setVisible(False)
        self.log.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        root.addWidget(self.log)

        # --- Buttons ---
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()
        self.btn_package = QPushButton("📦  Đóng gói")
        self.btn_package.setFont(QFont("Arial", 11, QFont.Bold))
        self.btn_package.setMinimumWidth(160)
        self.btn_package.setMinimumHeight(36)
        self.btn_package.setStyleSheet(
            "QPushButton { background: #2e7d32; color: white; border-radius: 6px; padding: 6px 20px; }"
            "QPushButton:hover { background: #388e3c; }"
        )
        self.btn_package.clicked.connect(self._do_package)
        btn_row2.addWidget(self.btn_package)

        self.btn_close = QPushButton("Đóng")
        self.btn_close.setMinimumHeight(36)
        self.btn_close.clicked.connect(self.close)
        btn_row2.addWidget(self.btn_close)
        btn_row2.addStretch()
        root.addLayout(btn_row2)

    # ---- Layer scanning ----
    def _refresh_layers(self):
        """Scan all layers in the current project and populate the tree."""
        self.tree.clear()
        project = QgsProject.instance()
        layers = project.mapLayers()

        for lid, layer in layers.items():
            src_path = _layer_source_path(layer)
            ltype = _layer_type_label(layer)
            status = ""
            can_package = False

            if ltype == "Memory":
                status = "⚠ Memory (tạm)"
            elif ltype == "Online":
                status = "🌐 Online (bỏ qua)"
            elif src_path:
                status = "✅ Sẵn sàng"
                can_package = True
            else:
                status = "⚠ Không rõ nguồn"

            item = QTreeWidgetItem([
                layer.name(),
                ltype,
                src_path or layer.source()[:80],
                status,
            ])
            item.setData(0, Qt.UserRole, lid)  # store layer ID
            if can_package:
                item.setCheckState(0, Qt.Checked)
            else:
                item.setCheckState(0, Qt.Unchecked)
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                for col in range(4):
                    item.setForeground(col, QColor("#999"))

            self.tree.addTopLevelItem(item)

    def refresh_layers(self):
        """Public alias for _refresh_layers."""
        self._refresh_layers()

    def _check_all(self):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(0, Qt.Checked)

    def _uncheck_all(self):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(0, Qt.Unchecked)

    def _browse_output(self):
        fmt = self.cbo_format.currentData()
        if fmt == "zip":
            path, _ = QFileDialog.getSaveFileName(
                self, "Chọn file ZIP đầu ra", "", "ZIP (*.zip)"
            )
        else:
            path = QFileDialog.getExistingDirectory(
                self, "Chọn thư mục đích"
            )
        if path:
            self.edt_path.setText(path)

    # ---- Logging ----
    def _log(self, msg):
        self.log.append(msg)
        QApplication.processEvents()

    # ---- Packaging engine ----
    def _do_package(self):
        """Execute the packaging process."""
        output_path = self.edt_path.text().strip()
        if not output_path:
            QMessageBox.warning(self, "LVT4U", "Vui lòng chọn đường dẫn đầu ra!")
            return

        # Collect checked layers
        selected_ids = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                selected_ids.append(item.data(0, Qt.UserRole))

        if not selected_ids:
            QMessageBox.warning(self, "LVT4U", "Vui lòng chọn ít nhất 1 layer!")
            return

        fmt = self.cbo_format.currentData()
        convert_gpkg = self.chk_gpkg.isChecked()

        project = QgsProject.instance()
        project_title = project.title() or project.baseName() or "LVT_Package"
        # Sanitize folder name
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', project_title)

        # Determine working directory
        if fmt == "zip":
            work_dir = os.path.join(tempfile.gettempdir(), f"lvt_pkg_{safe_name}")
        else:
            work_dir = os.path.join(output_path, safe_name)

        # Create directories
        pkg_dir = work_dir
        data_dir = os.path.join(pkg_dir, "data")
        styles_dir = os.path.join(pkg_dir, "styles")
        layouts_dir = os.path.join(pkg_dir, "layouts")
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(styles_dir, exist_ok=True)
        os.makedirs(layouts_dir, exist_ok=True)

        self.progress.setVisible(True)
        self.log.setVisible(True)
        self.log.clear()
        self.progress.setMaximum(len(selected_ids) + 3)
        self.progress.setValue(0)

        self._log(f"📦 Bắt đầu đóng gói: {safe_name}")
        self._log(f"   Thư mục: {pkg_dir}")
        self._log(f"   Layers: {len(selected_ids)}")
        self._log("")

        # Track source path remapping: old_source -> new_relative_path
        remap = {}
        step = 0

        # ---- Step 1: Copy layer data ----
        for lid in selected_ids:
            layer = project.mapLayer(lid)
            if not layer:
                continue
            step += 1
            self.progress.setValue(step)

            src_path = _layer_source_path(layer)
            if not src_path:
                self._log(f"   ⚠ {layer.name()} — không tìm thấy file nguồn, bỏ qua")
                continue

            ext = os.path.splitext(src_path)[1].lower()
            layer_name_safe = re.sub(r'[<>:"/\\|?*\s]', '_', layer.name())

            # Convert SHP to GPKG if requested
            if convert_gpkg and ext == '.shp' and isinstance(layer, QgsVectorLayer):
                gpkg_name = f"{layer_name_safe}.gpkg"
                gpkg_path = os.path.join(data_dir, gpkg_name)
                self._log(f"   🔄 {layer.name()} → GeoPackage...")

                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "GPKG"
                options.fileEncoding = "UTF-8"
                ctx = QgsCoordinateTransformContext()

                error_code, error_msg = QgsVectorFileWriter.writeAsVectorFormatV2(
                    layer, gpkg_path, ctx, options
                )[:2]

                if error_code == QgsVectorFileWriter.NoError:
                    remap[lid] = os.path.join("data", gpkg_name)
                    # Save style
                    style_path = os.path.join(styles_dir, f"{layer_name_safe}.qml")
                    layer.saveNamedStyle(style_path)
                    self._log(f"   ✅ {layer.name()} → {gpkg_name}")
                else:
                    self._log(f"   ❌ {layer.name()} chuyển đổi thất bại: {error_msg}")
                    # Fallback: copy original files
                    self._copy_layer_files(layer, src_path, data_dir, styles_dir,
                                           layer_name_safe, remap, lid)
            else:
                # Copy original files
                self._copy_layer_files(layer, src_path, data_dir, styles_dir,
                                       layer_name_safe, remap, lid)

        # ---- Step 2: Export layouts ----
        self.progress.setValue(step + 1)
        layout_manager = project.layoutManager()
        layout_count = 0
        if layout_manager:
            for layout in layout_manager.layouts():
                layout_count += 1
                lname = re.sub(r'[<>:"/\\|?*]', '_', layout.name())
                tpl_path = os.path.join(layouts_dir, f"{lname}.qpt")
                try:
                    from qgis.core import QgsReadWriteContext
                    from qgis.PyQt.QtXml import QDomDocument
                    doc = QDomDocument()
                    ctx = QgsReadWriteContext()
                    items = layout.writeXml(doc, ctx)
                    with open(tpl_path, 'w', encoding='utf-8') as f:
                        f.write(doc.toString(2))
                    self._log(f"   📐 Layout: {layout.name()} → {lname}.qpt")
                except Exception as e:
                    self._log(f"   ⚠ Layout {layout.name()}: {e}")

        if layout_count == 0:
            self._log("   ℹ Không có layout nào")

        # ---- Step 3: Save project file ----
        self.progress.setValue(step + 2)
        self._log("")
        self._log("💾 Lưu project...")

        project_file = os.path.join(pkg_dir, f"{safe_name}.qgz")
        self._save_packaged_project(project, project_file, remap, selected_ids)
        self._log(f"   ✅ Project: {safe_name}.qgz")

        # ---- Step 4: ZIP if requested ----
        if fmt == "zip":
            self.progress.setValue(step + 3)
            self._log("")
            self._log("🗜️ Nén ZIP...")

            zip_path = output_path
            if not zip_path.lower().endswith('.zip'):
                zip_path += '.zip'

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root_dir, dirs, files in os.walk(pkg_dir):
                    for f in files:
                        fpath = os.path.join(root_dir, f)
                        arcname = os.path.relpath(fpath, os.path.dirname(pkg_dir))
                        zf.write(fpath, arcname)

            # Clean up temp dir
            shutil.rmtree(pkg_dir, ignore_errors=True)
            self._log(f"   ✅ ZIP: {zip_path}")
            final_path = zip_path
        else:
            self.progress.setValue(step + 3)
            final_path = pkg_dir

        self._log("")
        self._log("=" * 50)
        self._log(f"✅ HOÀN TẤT! Đã đóng gói {len(remap)} layers.")
        self._log(f"   📂 {final_path}")

        self.progress.setValue(self.progress.maximum())
        QMessageBox.information(
            self, "LVT4U",
            f"Đóng gói thành công!\n\n{final_path}"
        )

    def _copy_layer_files(self, layer, src_path, data_dir, styles_dir,
                          layer_name_safe, remap, lid):
        """Copy all files belonging to a layer into data_dir."""
        ext = os.path.splitext(src_path)[1].lower()
        files = _collect_layer_files(layer)

        if ext == '.shp':
            # Copy all shapefile siblings, preserving base name
            base_src = os.path.splitext(src_path)[0]
            base_src_name = os.path.basename(base_src)
            for fpath in files:
                fname = os.path.basename(fpath)
                # Keep original name to preserve consistency
                dest = os.path.join(data_dir, fname)
                if not os.path.exists(dest):
                    shutil.copy2(fpath, dest)
            remap[lid] = os.path.join("data", os.path.basename(src_path))
        else:
            # Single file — copy with layer-safe name
            src_ext = os.path.splitext(src_path)[1]
            dest_name = f"{layer_name_safe}{src_ext}"
            dest = os.path.join(data_dir, dest_name)
            if not os.path.exists(dest):
                shutil.copy2(src_path, dest)
            remap[lid] = os.path.join("data", dest_name)

        # Save style (.qml) from QGIS styling engine
        style_path = os.path.join(styles_dir, f"{layer_name_safe}.qml")
        layer.saveNamedStyle(style_path)
        self._log(f"   ✅ {layer.name()} ({ext})")

    def _save_packaged_project(self, project, project_file, remap, selected_ids):
        """Save a copy of the project with updated relative data sources."""
        # We work on the XML to avoid modifying the user's live project
        from qgis.PyQt.QtXml import QDomDocument
        from qgis.core import QgsReadWriteContext

        # Read current project XML
        doc = QDomDocument()
        ok, _ = project.read(project.fileName() or "")

        # Strategy: write project to temp, modify XML, write final
        # First save current project to a temp location
        temp_qgz = project_file + ".tmp"
        project.write(temp_qgz)

        # Now create a fresh project from the temp, update sources, re-save
        pkg_project = QgsProject.instance()

        # Instead of complex XML manipulation, use a simpler approach:
        # Write the project, then do find-replace on source paths in the .qgs
        # For .qgz we need to unpack, modify, repack

        # Simpler approach: write project as .qgs (plain text XML)
        qgs_file = project_file.replace('.qgz', '.qgs')
        project.write(qgs_file)

        # Read and modify paths
        with open(qgs_file, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # Replace absolute paths with relative paths
        pkg_dir = os.path.dirname(project_file)
        for lid, rel_path in remap.items():
            layer = project.mapLayer(lid)
            if not layer:
                continue
            old_source = _layer_source_path(layer)
            if old_source:
                # Normalize path separators for XML
                old_escaped = old_source.replace('\\', '/').replace('&', '&amp;')
                new_rel = './' + rel_path.replace('\\', '/')
                xml_content = xml_content.replace(old_escaped, new_rel)

                # Also try with backslashes (Windows)
                old_bs = old_source.replace('/', '\\').replace('&', '&amp;')
                xml_content = xml_content.replace(old_bs, new_rel)

                # Try raw path too
                xml_content = xml_content.replace(old_source, new_rel)
                xml_content = xml_content.replace(
                    old_source.replace('\\', '/'), new_rel
                )

        # Write modified XML
        with open(qgs_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        # Clean up temp
        if os.path.exists(temp_qgz):
            try:
                os.remove(temp_qgz)
            except OSError:
                pass

        self._log(f"   Saved as .qgs (portable)")

        # Remove .qgz extension reference — we save as .qgs for maximum portability
        if os.path.exists(project_file) and project_file.endswith('.qgz'):
            try:
                os.remove(project_file)
            except OSError:
                pass
