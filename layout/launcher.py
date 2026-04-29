# -*- coding: utf-8 -*-
"""
LVT Map Layout - Main Plugin Class
Manages plugin lifecycle: toolbar button, menu entry, and dialog.
"""

import os

from qgis.PyQt.QtCore import QCoreApplication, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction


class LvtMapLayout:
    """Main QGIS Plugin class for LVT Map Layout."""

    def __init__(self, iface):
        """Constructor.

        Args:
            iface: A QGIS interface instance (QgisInterface).
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr("&LVT Map Layout")
        self.toolbar = self.iface.addToolBar("LVT Map Layout")
        self.toolbar.setObjectName("LvtMapLayoutToolbar")
        self.dlg = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Translate a string using Qt translation API."""
        return QCoreApplication.translate("LvtMapLayout", message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon and menu entry.

        Args:
            icon_path: Path to the icon for this action.
            text: Text displayed in menu and tooltip.
            callback: Function called when action is triggered.
            enabled_flag: Whether the action is enabled by default.
            add_to_menu: Whether to add to the plugin menu.
            add_to_toolbar: Whether to add to the toolbar.
            status_tip: Optional status bar text.
            whats_this: Optional What's This text.
            parent: Parent widget for the action.

        Returns:
            QAction: The created action.
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        if not os.path.exists(icon_path):
            icon_path = ":/images/themes/default/mActionNewLayout.svg"

        self.add_action(
            icon_path,
            text=self.tr("LVT Map Layout"),
            callback=self.run,
            parent=self.iface.mainWindow(),
            status_tip=self.tr("Generate map layout from LVT templates"),
        )

    def unload(self):
        """Remove the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr("&LVT Map Layout"), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """Show the plugin dialog."""
        from .lvt_dialog import LvtDialog

        if self.dlg is None:
            self.dlg = LvtDialog(self.iface, self.plugin_dir)

        self.dlg.refresh_layers()
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()
