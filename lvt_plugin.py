# -*- coding: utf-8 -*-
"""
LVT Plugin Suite — Menu Coordinator.

Creates the top-level "LVT" menu on the QGIS menu bar and registers
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

    PLUGIN_NAME = "LVT"

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

        # --- Map Layout ---
        self._add_action("layout.png", "Map Layout", self._open_layout)

        self.lvt_menu.addSeparator()

        # --- KML (submenu) ---
        kml_sub = self._add_submenu("kml.png", "KML")
        self._add_action("kml.png", "SHP → KML/KMZ", self._open_kml_export, kml_sub)
        self._add_action("kml.png", "KML/KMZ → SHP", self._open_kml_import, kml_sub)

        self.lvt_menu.addSeparator()

        # --- Data Tools ---
        self._add_action("mbtiles.png", "Create MBTiles", self._open_mbtiles)
        self._add_action("eudr.png", "Create GeoJSON EUDR", self._open_eudr)
        self._add_action("package.png", "Package Map", self._open_packager)

        self.lvt_menu.addSeparator()

        # --- Thematic Map (submenu) ---
        thematic_sub = self._add_submenu("thematic.png", "Thematic Map")
        self._add_action(
            "thematic.png", "Circular 16/2023", self._open_thematic_tt16, thematic_sub
        )
        self._add_action(
            "thematic.png", "Plot Labels", self._open_thematic_labels, thematic_sub
        )

        self.lvt_menu.addSeparator()

        # --- Basemap (submenu) ---
        basemap_sub = self._add_submenu("basemap.png", "Basemap")
        self._add_action(
            "basemap.png", "Google Maps", self._load_basemap_maps, basemap_sub
        )
        self._add_action(
            "basemap.png", "Google Satellite", self._load_basemap_satellite, basemap_sub
        )
        self._add_action(
            "basemap.png", "Google Hybrid", self._load_basemap_hybrid, basemap_sub
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
    # Module Launchers (Lazy Loading)
    # ------------------------------------------------------------------

    def _open_layout(self):
        """Open the Map Layout dialog."""
        self._show_placeholder("Map Layout")

    def _open_kml_export(self):
        """Open the SHP to KML/KMZ dialog."""
        self._show_placeholder("SHP → KML/KMZ")

    def _open_kml_import(self):
        """Open the KML/KMZ to SHP dialog."""
        self._show_placeholder("KML/KMZ → SHP")

    def _open_mbtiles(self):
        """Open the MBTiles creator dialog."""
        self._show_placeholder("Create MBTiles")

    def _open_eudr(self):
        """Open the EUDR GeoJSON exporter dialog."""
        self._show_placeholder("GeoJSON EUDR")

    def _open_packager(self):
        """Open the Map Packager dialog."""
        self._show_placeholder("Package Map")

    def _open_thematic_tt16(self):
        """Open the Thematic Map (TT16/2023) dialog."""
        self._show_placeholder("Thematic Map — TT 16/2023")

    def _open_thematic_labels(self):
        """Open the Plot Labels dialog."""
        self._show_placeholder("Plot Labels")

    def _load_basemap_maps(self):
        """Add Google Maps basemap to the current project."""
        self._add_xyz_basemap(
            "Google Maps",
            "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        )

    def _load_basemap_satellite(self):
        """Add Google Satellite basemap to the current project."""
        self._add_xyz_basemap(
            "Google Satellite",
            "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        )

    def _load_basemap_hybrid(self):
        """Add Google Hybrid basemap to the current project."""
        self._add_xyz_basemap(
            "Google Hybrid",
            "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        )

    def _open_legal(self):
        """Open the Legal Documents dialog."""
        self._show_placeholder("Legal Documents")

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

    def _show_placeholder(self, module_name):
        """Display a message bar notification for modules not yet implemented.

        Args:
            module_name: Human-readable name of the module.
        """
        self.iface.messageBar().pushInfo(
            "LVT",
            tr("{module} — Coming soon!").format(module=module_name),
        )

    def _add_xyz_basemap(self, name, url):
        """Add an XYZ tile layer to the current QGIS project.

        Uses the standard XYZ tile URI format supported by QGIS raster provider.

        Args:
            name: Display name for the layer.
            url: XYZ tile URL template with {x}, {y}, {z} placeholders.
        """
        from qgis.core import QgsRasterLayer, QgsProject

        uri = (
            f"type=xyz&url={url}"
            f"&zmin=0&zmax=19"
        )

        # Avoid duplicates — check if a layer with this name already exists
        existing = QgsProject.instance().mapLayersByName(name)
        if existing:
            self.iface.messageBar().pushInfo(
                "LVT",
                tr("{name} is already loaded.").format(name=name),
            )
            return

        layer = QgsRasterLayer(uri, name, "wms")
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            self.iface.messageBar().pushSuccess(
                "LVT",
                tr("{name} added successfully.").format(name=name),
            )
        else:
            self.iface.messageBar().pushWarning(
                "LVT",
                tr("Failed to load {name}.").format(name=name),
            )
