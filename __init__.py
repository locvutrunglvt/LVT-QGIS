# -*- coding: utf-8 -*-
"""
LVT Plugin Suite — QGIS Plugin Package Initializer.

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""


def classFactory(iface):
    """Entry point called by QGIS to create the plugin instance.

    Args:
        iface: QgisInterface instance providing access to the QGIS environment.

    Returns:
        LvtPlugin: The plugin instance.
    """
    from .lvt_plugin import LvtPlugin
    return LvtPlugin(iface)
