# -*- coding: utf-8 -*-
"""LVT4U Package Map — Portable project packager.

Inspired by the Project Packager plugin (Tarot Osuji, GPL-2.0).
Simplified approach: copies all data files via GDAL, remaps layer
sources using QgsProviderRegistry, and writes a portable .qgz project.
"""
import os
import shutil

from osgeo import gdal
from qgis.PyQt.QtCore import Qt, QDir, QUrl, QStandardPaths
from qgis.PyQt.QtGui import QFont, QIcon
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox, QFormLayout,
    QProgressDialog, QApplication, QToolButton,
    QRadioButton, QCheckBox, QGroupBox, QGridLayout,
)
from qgis.core import (
    QgsApplication, QgsProject, QgsProviderRegistry,
    QgsDataProvider, QgsVectorDataProvider,
    QgsRenderContext, QgsLayoutItemPicture,
    QgsSymbolLayerUtils,
)


# =====================================================================
# Symbol / image path utilities (handles SVG, raster fills, layout pics)
# =====================================================================

# Stock SVG paths shipped with QGIS — we skip these
_stock_svgs = list(
    map(lambda x: QDir(x).canonicalPath(), QgsSymbolLayerUtils.listSvgFiles())
)


def _symbol_layers_from_symbol(symbol):
    """Recursively collect all symbol layers from a symbol."""
    slyrs = []
    for slyr in symbol.symbolLayers():
        sub = slyr.subSymbol()
        if sub:
            slyrs.extend(_symbol_layers_from_symbol(sub))
        slyrs.append(slyr)
    return slyrs


def _get_path(slyr):
    """Get the external file path from a symbol layer."""
    for getter in ('path', 'svgFilePath', 'imageFilePath'):
        try:
            return getattr(slyr, getter)()
        except AttributeError:
            pass
    return None


def _set_path(slyr, new_path):
    """Set the external file path on a symbol layer."""
    for setter in ('setPath', 'setSvgFilePath', 'setImageFilePath'):
        try:
            getattr(slyr, setter)(new_path)
            return
        except AttributeError:
            pass


def _collect_symbol_paths(project, context):
    """Map: symbol_layer_or_layout_item → absolute file path."""
    result = {}

    # Symbol layers in map layers
    for lyr in project.mapLayers().values():
        try:
            syms = lyr.renderer().symbols(context)
        except AttributeError:
            continue
        for sym in syms:
            for slyr in _symbol_layers_from_symbol(sym):
                raw = _get_path(slyr)
                path = QDir(raw).canonicalPath() if raw else ''
                if path and os.path.exists(path) and path not in _stock_svgs:
                    result[slyr] = path

    # Layout items (pictures + shape symbols)
    for layout in project.layoutManager().printLayouts():
        model = layout.itemsModel()
        for row in range(model.rowCount()):
            item = model.itemFromIndex(model.index(row, 0))
            if isinstance(item, QgsLayoutItemPicture):
                raw = item.picturePath()
                path = QDir(raw).canonicalPath() if raw else ''
                if path and os.path.exists(path) and path not in _stock_svgs:
                    result[item] = path
            else:
                try:
                    sym = item.symbol()
                except AttributeError:
                    continue
                for slyr in _symbol_layers_from_symbol(sym):
                    raw = _get_path(slyr)
                    path = QDir(raw).canonicalPath() if raw else ''
                    if path and os.path.exists(path) and path not in _stock_svgs:
                        result[slyr] = path

    return result


# =====================================================================
# Helpers
# =====================================================================

def _is_in_dir(parent, child):
    """Check if child path is inside parent directory."""
    parent = os.path.abspath(parent)
    child = os.path.abspath(child)
    try:
        return os.path.commonpath([parent, child]) == parent
    except ValueError:
        return False


def _get_source_info(layer):
    """Decode a layer's data provider URI into (path, layerName, options).

    Returns None if the layer is not file-based.
    """
    dp = layer.dataProvider()
    if dp is None:
        return None
    reg = QgsProviderRegistry.instance()
    parts = reg.decodeUri(dp.name(), layer.source())
    path = parts.get('path')
    if path:
        path = QDir(path).canonicalPath()
    if not path:
        return None
    layer_name = parts.get('layerName')
    return path, layer_name, None


# =====================================================================
# Dialog
# =====================================================================

class PackageMapDialog(QDialog):
    """Simple, effective project packager dialog."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("LVT4U — Package Map")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Header
        hdr = QLabel("📦  Package Map")
        hdr.setFont(QFont("Arial", 13, QFont.Bold))
        layout.addWidget(hdr)

        desc = QLabel(
            "Đóng gói project QGIS hiện tại thành thư mục di động.\n"
            "Toàn bộ dữ liệu, style, nhãn, layout được copy — mở trên máy khác hiển thị đúng."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Output folder
        form = QFormLayout()
        row = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_edit.setReadOnly(True)
        self.dir_edit.setMinimumWidth(400)
        row.addWidget(self.dir_edit)
        btn_browse = QToolButton()
        btn_browse.setIcon(QIcon(':/images/themes/default/mActionFileOpen.svg'))
        btn_browse.clicked.connect(self._browse)
        row.addWidget(btn_browse)
        form.addRow("Thư mục đích:", row)
        layout.addLayout(form)

        # Options
        grp = QGroupBox("Tùy chọn")
        grid = QGridLayout(grp)
        self.radio_copy = QRadioButton("Copy dữ liệu gốc (giữ nguyên định dạng)")
        self.radio_copy.setChecked(True)
        grid.addWidget(self.radio_copy, 0, 0, 1, 2)

        self.chk_vacuum = QCheckBox("Vacuum file SQLite sau khi copy")
        grid.addWidget(self.chk_vacuum, 1, 1)

        layout.addWidget(grp)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_run = QPushButton("📦  Đóng gói")
        self.btn_run.setFont(QFont("Arial", 11, QFont.Bold))
        self.btn_run.setMinimumHeight(36)
        self.btn_run.setMinimumWidth(150)
        self.btn_run.setStyleSheet(
            "QPushButton { background: #2e7d32; color: white; border-radius: 6px; padding: 6px 20px; }"
            "QPushButton:hover { background: #388e3c; }"
        )
        self.btn_run.clicked.connect(self._run)
        btn_row.addWidget(self.btn_run)

        btn_close = QPushButton("Đóng")
        btn_close.setMinimumHeight(36)
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.setMaximumHeight(0)  # compact

    def _browse(self):
        path = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục đích", self.dir_edit.text()
        )
        if path:
            self.dir_edit.setText(path)

    def refresh_layers(self):
        """No-op for interface compatibility."""
        pass

    # -----------------------------------------------------------------
    # Packaging engine
    # -----------------------------------------------------------------
    def _run(self):
        project = QgsProject.instance()

        # Must have a saved project
        if not project.fileName():
            QMessageBox.warning(
                self, "LVT4U",
                "Project chưa được lưu.\nHãy lưu project (Ctrl+S) trước khi đóng gói."
            )
            return

        if project.isDirty():
            QMessageBox.warning(
                self, "LVT4U",
                "Project có thay đổi chưa lưu.\nHãy lưu project (Ctrl+S) trước khi đóng gói."
            )
            return

        if not self.dir_edit.text():
            self._browse()
        if not self.dir_edit.text():
            return

        # Build source map: layer → (path, layerName, options)
        src_map = {}
        for lyr in project.mapLayers().values():
            info = _get_source_info(lyr)
            if info:
                src_map[lyr] = info

        if not src_map:
            QMessageBox.information(
                self, "LVT4U",
                "Không có layer file nào trong project hiện tại."
            )
            return

        # Determine output directory
        outdir = os.path.join(self.dir_edit.text(), project.baseName())
        home = project.homePath()
        if home and _is_in_dir(home, outdir):
            QMessageBox.warning(
                self, "LVT4U",
                "Thư mục đích không được nằm trong thư mục project!"
            )
            return

        # Handle existing folder
        if os.path.exists(outdir):
            res = QMessageBox.question(
                self, "LVT4U",
                f"Thư mục '{outdir}' đã tồn tại.\n"
                f"Dữ liệu cũ sẽ bị xóa. Tiếp tục?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if res != QMessageBox.Yes:
                return
            try:
                shutil.rmtree(outdir)
            except Exception as e:
                QMessageBox.critical(self, "LVT4U", f"Lỗi xóa thư mục: {e}")
                return

        # Collect symbol/image paths
        context = QgsRenderContext.fromMapSettings(
            self.iface.mapCanvas().mapSettings()
        )
        sym_map = _collect_symbol_paths(project, context)

        # Build unique path set (data + symbols)
        all_paths = [path for path, _, _ in src_map.values()]
        all_paths.extend(sym_map.values())
        paths_set = list(set(all_paths))

        # Create directory mapping: avoid name collisions
        dirs_set = list(set(os.path.dirname(p) for p in paths_set))
        names = [project.baseName() + '.qgz']  # reserve project name
        for d in dirs_set:
            name = os.path.basename(d)
            if name in names:
                suffix = 1
                while f"{name}_{suffix}" in names:
                    suffix += 1
                name = f"{name}_{suffix}"
            names.append(name)
        del names[0]  # remove reserved project name
        dir_map = dict(zip(dirs_set, names))
        path_map = {p: dir_map[os.path.dirname(p)] for p in paths_set}

        # Progress dialog
        pd = QProgressDialog(self.iface.mainWindow())
        pd.setWindowTitle("LVT4U — Đóng gói")
        pd.setAutoReset(False)
        pd.setMinimumDuration(0)
        pd.setWindowModality(Qt.WindowModal)
        pd.setMinimumWidth(400)
        pd.setMaximum(len(path_map) + 1)
        pd.setValue(0)

        orig_project = project.fileName()

        try:
            # ---- Copy files ----
            for path in path_map:
                if pd.wasCanceled():
                    return

                dstdir = os.path.join(outdir, path_map[path])
                os.makedirs(dstdir, exist_ok=True)

                # Use GDAL to get full file list (handles .shp siblings etc.)
                if os.path.isdir(path):
                    file_list = [path]
                else:
                    try:
                        ds = gdal.OpenEx(path)
                        file_list = ds.GetFileList() if ds else [path]
                    except (AttributeError, RuntimeError):
                        file_list = [path]
                    finally:
                        ds = None

                for fpath in file_list:
                    pd.setLabelText(f"Copying: {os.path.basename(fpath)}")
                    QgsApplication.processEvents()
                    try:
                        if os.path.isdir(fpath):
                            shutil.copytree(
                                fpath,
                                os.path.join(dstdir, os.path.basename(fpath))
                            )
                        else:
                            shutil.copy2(fpath, dstdir)
                    except FileNotFoundError:
                        pass
                    except (PermissionError, IsADirectoryError):
                        try:
                            shutil.copytree(
                                fpath,
                                os.path.join(dstdir, os.path.basename(fpath))
                            )
                        except Exception:
                            pass

                    # Vacuum SQLite if requested
                    if self.chk_vacuum.isChecked():
                        self._try_vacuum(
                            os.path.join(dstdir, os.path.basename(fpath)), pd
                        )

                pd.setValue(pd.value() + 1)

            if pd.wasCanceled():
                return

            # ---- Remap layer data sources ----
            reg = QgsProviderRegistry.instance()
            for lyr, src in src_map.items():
                path, _, _ = src
                dp = lyr.dataProvider()
                encoding = (dp.encoding()
                            if isinstance(dp, QgsVectorDataProvider) else None)
                parts = reg.decodeUri(dp.name(), lyr.source())
                parts['path'] = QDir(
                    os.path.join(outdir, path_map[path], os.path.basename(path))
                ).absolutePath()
                new_source = reg.encodeUri(dp.name(), parts)
                lyr.setDataSource(
                    new_source, lyr.name(), lyr.providerType(),
                    QgsDataProvider.ProviderOptions()
                )
                if encoding is not None:
                    lyr.dataProvider().setEncoding(encoding)

            # ---- Remap symbol/image paths ----
            for slyr, path in sym_map.items():
                new_path = QDir(
                    os.path.join(outdir, path_map[path], os.path.basename(path))
                ).absolutePath()
                if isinstance(slyr, QgsLayoutItemPicture):
                    fmt = (QgsLayoutItemPicture.FormatSVG
                           if new_path.endswith(('.svg', '.svgz'))
                           else QgsLayoutItemPicture.FormatRaster)
                    slyr.setPicturePath(new_path, fmt)
                else:
                    _set_path(slyr, new_path)

            # ---- Write project ----
            pd.setValue(pd.maximum())
            pd.setLabelText("Lưu project...")
            QgsApplication.processEvents()

            project.setPresetHomePath('')
            project.writeEntryBool('Paths', '/Absolute', False)
            qgz_path = QDir(
                os.path.join(outdir, project.baseName())
            ).absolutePath() + '.qgz'
            result = project.write(qgz_path)

        except Exception as e:
            QMessageBox.critical(self, "LVT4U", f"Lỗi đóng gói: {e}")
            return
        finally:
            pd.hide()
            pd.deleteLater()
            # Reload original project to restore live state
            mb = self.iface.messageBar()
            mb.widgetAdded.connect(mb.popWidget)
            project.read(orig_project)
            mb.widgetAdded.disconnect(mb.popWidget)

        if result:
            self.iface.messageBar().pushSuccess(
                "LVT4U",
                f'Đóng gói thành công! → <a href="{QUrl.fromLocalFile(outdir).toString()}">{outdir}</a>'
            )
            self.close()
        else:
            QMessageBox.warning(
                self, "LVT4U", "Lưu project thất bại!"
            )

    @staticmethod
    def _try_vacuum(filepath, pd):
        """Vacuum a SQLite file if detected."""
        import sqlite3
        from contextlib import closing
        try:
            with open(filepath, 'rb') as f:
                header = f.read(16)
            if header == b'SQLite format 3\x00':
                pd.setLabelText(f"Vacuum: {os.path.basename(filepath)}")
                QgsApplication.processEvents()
                with closing(sqlite3.connect(filepath)) as conn:
                    conn.execute('VACUUM')
        except Exception:
            pass
