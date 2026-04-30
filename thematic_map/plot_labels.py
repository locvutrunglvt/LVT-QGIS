# -*- coding: utf-8 -*-
"""
LVT4U Plot Labels — Standalone Forest Plot Labeling Engine.

Reuses the label engine from the MBTiles module but removes all
MBTiles-specific functionality (Extent, Zoom, Export).
This allows users to style and apply plot labels to any vector layer
without creating MBTiles.

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""
from qgis.PyQt.QtCore import Qt

from ..mbtiles.dialog import MBTilesDialog, _tr


class PlotLabelsDialog(MBTilesDialog):
    """Standalone plot labeling dialog.

    Inherits all label-building, preview, buffer/background, and
    apply-style functionality from MBTilesDialog.
    Hides Extent/Zoom/Export sections so the user focuses purely on
    label design.
    """

    def __init__(self, iface, parent=None):
        super().__init__(iface, parent)
        # Hide MBTiles-specific sections
        self.grp_extent.setVisible(False)
        self.btn_export.setVisible(False)
        # Hide polygon styling (stroke/fill) — pure labels only
        self.grp_style.setVisible(False)
        # Retitle
        self._refresh_window_title()

    def _refresh_window_title(self):
        """Set the window title appropriate for standalone labeling."""
        if self.lang == 'vi':
            self.setWindowTitle("LVT4U — Nhãn lô rừng")
        else:
            self.setWindowTitle("LVT4U — Plot Labels")

    def _toggle_lang(self):
        """Override to also update custom title."""
        super()._toggle_lang()
        self._refresh_window_title()

    def _refresh_ui_text(self):
        """Override to customize title and tab names."""
        super()._refresh_ui_text()
        self._refresh_window_title()
        if self.lang == 'vi':
            self.tabs.setTabText(0, "Nhãn lô rừng")
        else:
            self.tabs.setTabText(0, "Plot Labels")
