# -*- coding: utf-8 -*-
"""
LVT4U Plugin Suite — Menu Coordinator.

Creates the top-level "LVT4U" menu on the QGIS menu bar and registers
all sub-module actions. Each module is loaded on-demand when the user
clicks the corresponding menu item.

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0

Scientific basis:
    - QGIS API Documentation (docs.qgis.org)
    - Cartographic standards for menu organization
"""

import os

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu

from .shared.i18n import tr, current_language


class LvtPlugin:
    """Top-level orchestrator for the LVT Plugin Suite.

    Responsibilities:
        - Create and manage the "LVT" menu on the QGIS menu bar
        - Register menu items for each module
        - Lazy-load module dialogs on first use
    """

    PLUGIN_NAME = "LVT4U"

    def __init__(self, iface):
        """Initialize the plugin.

        Args:
            iface: QgisInterface instance for interacting with the QGIS environment.
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.lvt_menu = None
        self.actions = []
        self.submenus = []

        # Module dialog instances (lazy-loaded)
        self._dialogs = {}

    # ------------------------------------------------------------------
    # QGIS Plugin Lifecycle
    # ------------------------------------------------------------------

    def initGui(self):
        """Build the LVT menu and insert it into the QGIS menu bar."""
        self.lvt_menu = QMenu(self.PLUGIN_NAME)
        self.iface.mainWindow().menuBar().insertMenu(
            self.iface.firstRightStandardMenu().menuAction(),
            self.lvt_menu,
        )
        self._build_menu()
        self._install_style_library()

    def unload(self):
        """Remove the LVT menu from the QGIS menu bar and clean up."""
        if self.lvt_menu:
            self.iface.mainWindow().menuBar().removeAction(
                self.lvt_menu.menuAction()
            )
            self.lvt_menu.deleteLater()
            self.lvt_menu = None

        self.actions.clear()
        self.submenus.clear()
        self._dialogs.clear()

    # ------------------------------------------------------------------
    # Menu Construction
    # ------------------------------------------------------------------

    def _icon(self, name):
        """Resolve an icon path from the icons/ directory.

        Args:
            name: Icon filename (e.g. "layout.png").

        Returns:
            QIcon instance, or empty QIcon if file not found.
        """
        path = os.path.join(self.plugin_dir, "icons", name)
        return QIcon(path) if os.path.isfile(path) else QIcon()

    def _add_action(self, icon_name, text, callback, menu=None):
        """Create a QAction and add it to the specified menu.

        Args:
            icon_name: Filename of the icon in icons/.
            text: Display text (will be translated).
            callback: Callable invoked when the action is triggered.
            menu: Target QMenu. Defaults to the top-level LVT menu.

        Returns:
            QAction: The created action.
        """
        action = QAction(self._icon(icon_name), tr(text), self.iface.mainWindow())
        action.triggered.connect(callback)
        target = menu if menu is not None else self.lvt_menu
        target.addAction(action)
        self.actions.append(action)
        return action

    def _add_submenu(self, icon_name, text):
        """Create a submenu under the LVT menu.

        Args:
            icon_name: Filename of the icon in icons/.
            text: Display text (will be translated).

        Returns:
            QMenu: The created submenu.
        """
        submenu = QMenu(tr(text), self.iface.mainWindow())
        submenu.setIcon(self._icon(icon_name))
        self.lvt_menu.addMenu(submenu)
        self.submenus.append(submenu)
        return submenu

    def _build_menu(self):
        """Assemble the complete LVT menu structure."""

        # --- Basemap (submenu with provider sub-groups) ---
        basemap_sub = self._add_submenu("basemap.png", "Basemap")
        self._build_basemap_menu(basemap_sub)

        self.lvt_menu.addSeparator()

        # --- Map Layout ---
        self._add_action("layout.png", "Map Layout", self._open_layout)

        self.lvt_menu.addSeparator()

        # --- KML (submenu) ---
        kml_sub = self._add_submenu("kml.png", "KML")
        self._add_action("kml.png", "SHP → KML/KMZ", self._open_kml_export, kml_sub)
        self._add_action("kml.png", "KML/KMZ → SHP", self._open_kml_import, kml_sub)

        self.lvt_menu.addSeparator()

        # --- EUDR (submenu) ---
        eudr_sub = self._add_submenu("eudr.png", "EUDR")
        self._add_action(
            "eudr.png", "Export GeoJSON", self._open_eudr, eudr_sub
        )
        self._add_action(
            "eudr.png", "Reference Documents",
            self._open_eudr_reference, eudr_sub
        )

        self.lvt_menu.addSeparator()

        # --- Data Tools ---
        self._add_action("mbtiles.png", "Create MBTiles", self._open_mbtiles)
        self._add_action("package.png", "Package Map", self._open_packager)
        self._add_action("excel.png", "Excel → GIS", self._open_excel_gis)

        self.lvt_menu.addSeparator()

        # --- Thematic Map (submenu) ---
        thematic_sub = self._add_submenu("thematic.png", "Forest Status Thematic Map")
        self._add_action(
            "thematic.png", "Circular 16/2023", self._open_thematic_tt16, thematic_sub
        )
        thematic_sub.addSeparator()
        self._add_action(
            "thematic.png", "Create Plot Labels", self._open_thematic_labels, thematic_sub
        )

        self.lvt_menu.addSeparator()

        # --- Utilities ---
        self._add_action("legal.png", "Legal Documents", self._open_legal)
        self._add_action("font.png", "Font Converter", self._open_font)

        self.lvt_menu.addSeparator()

        # --- CRS Tools (submenu) ---
        crs_sub = self._add_submenu("crs.png", "Coordinate System")
        self._add_action("crs.png", "CRS Conversion", self._open_crs_convert, crs_sub)
        self._add_action("crs.png", "Define CRS", self._open_crs_define, crs_sub)
        self._add_action("crs.png", "CRS Catalog", self._open_crs_catalog, crs_sub)

        self.lvt_menu.addSeparator()

        # --- About ---
        self._add_action("about.png", "About", self._open_about)

    # ------------------------------------------------------------------
    # Basemap Registry
    # ------------------------------------------------------------------

    # Basemap catalog: (display_name, url, zmin, zmax)
    _BASEMAPS = {
        "🌍 Google": [
            ("Google Maps",
             "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", 0, 22),
            ("Google Satellite",
             "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", 0, 22),
            ("Google Hybrid",
             "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", 0, 22),
            ("Google Terrain Hybrid",
             "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}", 0, 19),
        ],
        "🗺️ Esri": [
            ("Esri Satellite",
             "https://server.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", 0, 22),
            ("Esri Street",
             "https://server.arcgisonline.com/arcgis/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}", 0, 22),
            ("Esri Topographic",
             "https://server.arcgisonline.com/arcgis/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", 0, 22),
            ("Esri National Geographic",
             "https://server.arcgisonline.com/arcgis/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}", 0, 22),
            ("Esri Gray (light)",
             "https://server.arcgisonline.com/arcgis/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", 0, 16),
            ("Esri Gray (dark)",
             "https://server.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", 0, 16),
            ("Esri Physical",
             "https://server.arcgisonline.com/arcgis/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}", 0, 22),
            ("Esri Shaded Relief",
             "https://server.arcgisonline.com/arcgis/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}", 0, 13),
            ("Esri Terrain",
             "https://server.arcgisonline.com/arcgis/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}", 0, 13),
        ],
        "🎨 CartoDB": [
            ("Carto Light",
             "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png", 0, 20),
            ("Carto Dark",
             "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", 0, 20),
            ("Carto Antique",
             "https://cartocdn_a.global.ssl.fastly.net/base-antique/{z}/{x}/{y}.png", 0, 20),
            ("Carto Eco",
             "https://cartocdn_a.global.ssl.fastly.net/base-eco/{z}/{x}/{y}.png", 0, 20),
        ],
        "🗾 OpenStreetMap": [
            ("OpenStreetMap",
             "https://tile.openstreetmap.org/{z}/{x}/{y}.png", 0, 19),
            ("OpenTopoMap",
             "https://tile.opentopomap.org/{z}/{x}/{y}.png", 1, 17),
        ],
        "🌐 Bing": [
            ("Bing VirtualEarth",
             "https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1", 0, 22),
        ],
        "🔷 Other": [
            ("F4 Map 2D",
             "https://tile1.f4map.com/tiles/f4_2d/{z}/{x}/{y}.png", 0, 22),
        ],
    }

    def _build_basemap_menu(self, parent_menu):
        """Build hierarchical basemap menu from the registry."""
        for group_label, layers in self._BASEMAPS.items():
            group_menu = QMenu(group_label, self.iface.mainWindow())
            group_menu.setIcon(self._icon("basemap.png"))
            parent_menu.addMenu(group_menu)
            self.submenus.append(group_menu)
            for name, url, zmin, zmax in layers:
                action = QAction(
                    self._icon("basemap.png"), name,
                    self.iface.mainWindow(),
                )
                action.triggered.connect(
                    lambda checked, n=name, u=url, lo=zmin, hi=zmax:
                        self._add_xyz_basemap(n, u, lo, hi)
                )
                group_menu.addAction(action)
                self.actions.append(action)

    # ------------------------------------------------------------------
    # Module Launchers (Lazy Loading)
    # ------------------------------------------------------------------

    def _open_layout(self):
        """Open the Map Layout dialog."""
        from .layout.dialog import LvtDialog

        if "layout" not in self._dialogs:
            layout_dir = os.path.join(self.plugin_dir, "layout")
            self._dialogs["layout"] = LvtDialog(self.iface, layout_dir)

        dlg = self._dialogs["layout"]
        dlg.refresh_layers()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_kml_export(self):
        """Open the KML dialog (SHP to KML/KMZ tab)."""
        self._ensure_kml_dialog()
        dlg = self._dialogs["kml"]
        dlg.tabs.setCurrentIndex(0)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_kml_import(self):
        """Open the KML dialog (KML/KMZ to SHP tab)."""
        self._ensure_kml_dialog()
        dlg = self._dialogs["kml"]
        dlg.tabs.setCurrentIndex(1)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _ensure_kml_dialog(self):
        """Lazy-create the KML dialog instance."""
        if "kml" not in self._dialogs:
            from .kml.dialog import LvtKmlViewDialog
            self._dialogs["kml"] = LvtKmlViewDialog(
                self.iface, self.iface.mainWindow()
            )

    def _open_mbtiles(self):
        """Open the MBTiles creator dialog."""
        if "mbtiles" not in self._dialogs:
            from .mbtiles.dialog import MBTilesDialog
            self._dialogs["mbtiles"] = MBTilesDialog(self.iface)

        dlg = self._dialogs["mbtiles"]
        dlg.refresh_layers()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_eudr(self):
        """Open the EUDR GeoJSON exporter dialog."""
        if "eudr" not in self._dialogs:
            from .eudr.dialog import EudrExportDialog
            self._dialogs["eudr"] = EudrExportDialog(self.iface)

        dlg = self._dialogs["eudr"]
        dlg.refresh_layers()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_eudr_reference(self):
        """Open the EUDR Reference Documents dialog."""
        if "eudr_ref" not in self._dialogs:
            from .eudr.reference_dialog import EudrReferenceDialog
            self._dialogs["eudr_ref"] = EudrReferenceDialog(self.iface)

        dlg = self._dialogs["eudr_ref"]
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_packager(self):
        """Open the Map Packager dialog."""
        if "packager" not in self._dialogs:
            from .map_packager.dialog import PackageMapDialog
            self._dialogs["packager"] = PackageMapDialog(self.iface)

        dlg = self._dialogs["packager"]
        dlg.refresh_layers()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_thematic_tt16(self):
        """Open the Thematic Map (TT16/2023) dialog."""
        if "tt16" not in self._dialogs:
            from .thematic_map.tt16_dialog import TT16Dialog
            self._dialogs["tt16"] = TT16Dialog(self.iface)

        dlg = self._dialogs["tt16"]
        dlg.refresh_layers()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_thematic_tt33(self):
        """Open the Thematic Map (TT33) dialog."""
        self._show_placeholder("Thematic Map — TT 33")

    def _open_thematic_labels(self):
        """Open the standalone Plot Labels dialog."""
        if "plot_labels" not in self._dialogs:
            from .thematic_map.plot_labels import PlotLabelsDialog
            self._dialogs["plot_labels"] = PlotLabelsDialog(self.iface)

        dlg = self._dialogs["plot_labels"]
        dlg.refresh_layers()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_excel_gis(self):
        """Open the Excel → GIS importer dialog."""
        if "excel_gis" not in self._dialogs:
            from .excel_gis.dialog import ExcelGisDialog
            self._dialogs["excel_gis"] = ExcelGisDialog(self.iface)

        dlg = self._dialogs["excel_gis"]
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_legal(self):
        """Open the Legal Documents Library dialog."""
        if "legal" not in self._dialogs:
            from .legal_docs.dialog import LegalDocsDialog
            self._dialogs["legal"] = LegalDocsDialog(self.iface)

        dlg = self._dialogs["legal"]
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_font(self):
        """Open the Font Converter dialog."""
        self._show_placeholder("Font Converter")

    def _open_crs_convert(self):
        """Open the CRS Conversion dialog."""
        self._show_placeholder("CRS Conversion")

    def _open_crs_define(self):
        """Open the CRS Definition dialog."""
        self._show_placeholder("Define CRS")

    def _open_crs_catalog(self):
        """Open the CRS Catalog dialog."""
        self._show_placeholder("CRS Catalog")

    def _open_about(self):
        """Open the About dialog."""
        from .about.dialog import AboutDialog

        if "about" not in self._dialogs:
            self._dialogs["about"] = AboutDialog(self.iface, self.plugin_dir)
        self._dialogs["about"].exec_()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _install_style_library(self):
        """Import the TCVN 11565-2016 symbol library into QGIS Style Manager.

        Runs once per user profile. Uses QSettings flag to avoid re-importing
        on every plugin load.
        """
        settings_key = "LVT4U/style_imported_v1"
        if QSettings().value(settings_key, False, type=bool):
            return  # Already imported

        xml_path = os.path.join(
            self.plugin_dir, "thematic_map", "data",
            "tcvn11565_style.xml"
        )
        if not os.path.isfile(xml_path):
            return

        try:
            from qgis.core import QgsStyle
            style = QgsStyle.defaultStyle()
            count_before = style.symbolCount()
            ok = style.importXml(xml_path)
            if ok:
                count_after = style.symbolCount()
                added = count_after - count_before
                QSettings().setValue(settings_key, True)
                self.iface.messageBar().pushSuccess(
                    "LVT4U",
                    f"✅ TCVN 11565-2016 style library installed "
                    f"({added} symbols added to Style Manager)"
                )
            else:
                self.iface.messageBar().pushWarning(
                    "LVT4U",
                    "⚠️ Failed to import TCVN 11565-2016 style library"
                )
        except Exception as e:
            self.iface.messageBar().pushWarning(
                "LVT4U",
                f"⚠️ Style import error: {e}"
            )

    def _show_placeholder(self, module_name):
        """Display a message bar notification for modules not yet implemented.

        Args:
            module_name: Human-readable name of the module.
        """
        self.iface.messageBar().pushInfo(
            "LVT4U",
            tr("{module} — Coming soon!").format(module=module_name),
        )

    def _add_xyz_basemap(self, name, url, zmin=0, zmax=19):
        """Add an XYZ tile layer to the current QGIS project.

        Uses the standard XYZ tile URI format supported by QGIS raster provider.

        Args:
            name: Display name for the layer.
            url: XYZ tile URL template with {x}, {y}, {z} placeholders.
            zmin: Minimum zoom level (default 0).
            zmax: Maximum zoom level (default 19).
        """
        from qgis.core import QgsRasterLayer, QgsProject
        from urllib.parse import quote as _url_quote

        # URL-encode the tile URL so that '&' inside it won't clash
        # with the '&' separating QGIS URI parameters.
        encoded_url = _url_quote(url, safe=':/{}.?%')

        uri = (
            f"type=xyz&url={encoded_url}"
            f"&zmin={zmin}&zmax={zmax}"
        )

        # Avoid duplicates — check if a layer with this name already exists
        existing = QgsProject.instance().mapLayersByName(name)
        if existing:
            self.iface.messageBar().pushInfo(
                "LVT4U",
                tr("{name} is already loaded.").format(name=name),
            )
            return

        layer = QgsRasterLayer(uri, name, "wms")
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            self.iface.messageBar().pushSuccess(
                "LVT4U",
                tr("{name} added successfully.").format(name=name),
            )
        else:
            self.iface.messageBar().pushWarning(
                "LVT4U",
                tr("Failed to load {name}.").format(name=name),
            )
