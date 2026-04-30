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

    def _apply_to_layer(self):
        """Apply ONLY labels — no polygon styling (stroke/fill).

        Overrides the parent MBTilesDialog._apply_to_layer to skip
        polygon renderer changes, preserving any existing thematic map
        styling on the layer.
        """
        layer = self._get_layer()
        if not layer:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(self, "LVT4U", self._t("No vector layer."))
            return

        from qgis.PyQt.QtWidgets import QApplication, QMessageBox
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.progress.setFormat("Applying labels... %p%")
        QApplication.processEvents()

        # Skip polygon styling entirely — only apply labels
        self.progress.setValue(40)
        QApplication.processEvents()

        if self.chk_show_label.isChecked():
            expr = self._build_expression()
            if expr:
                from qgis.core import (
                    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling,
                    QgsTextFormat, QgsTextBufferSettings, QgsUnitTypes,
                )
                from qgis.PyQt.QtCore import QSizeF

                s = QgsPalLayerSettings()
                s.fieldName = expr
                s.isExpression = True
                s.scaleVisibility = True
                s.maximumScale = self.cbo_zoom_in.currentData()
                s.minimumScale = self.cbo_zoom_out.currentData()

                fmt = QgsTextFormat()
                font = self.cbo_font.currentFont()
                font.setPointSize(self.spn_fsize.value())
                font.setBold(self.chk_bold.isChecked())
                fmt.setFont(font)
                fmt.setColor(self._font_color)
                fmt.setSize(self.spn_fsize.value())

                lh_pct = self.spn_line_h.value() / 100.0
                try:
                    fmt.setLineHeightUnit(QgsUnitTypes.RenderPercentage)
                    fmt.setLineHeight(lh_pct)
                except Exception:
                    try:
                        from qgis.core import Qgis
                        fmt.setLineHeightUnit(Qgis.RenderUnit.Percentage)
                        fmt.setLineHeight(lh_pct)
                    except Exception:
                        fmt.setLineHeight(lh_pct)

                buf = QgsTextBufferSettings()
                buf.setEnabled(self.chk_buffer.isChecked())
                buf.setSize(self.spn_buf_size.value())
                buf.setColor(self._buf_color)
                fmt.setBuffer(buf)

                if self.chk_bg.isChecked():
                    from qgis.core import QgsTextBackgroundSettings
                    bg = QgsTextBackgroundSettings()
                    bg.setEnabled(True)
                    bg.setType(QgsTextBackgroundSettings.ShapeRectangle)
                    bg.setSizeType(QgsTextBackgroundSettings.SizeBuffer)
                    bg.setSize(QSizeF(1, 0.5))
                    bg.setFillColor(self._bg_color)
                    r = self.spn_bg_radius.value()
                    bg.setRadii(QSizeF(r, r))
                    fmt.setBackground(bg)

                s.setFormat(fmt)
                layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
                layer.setLabelsEnabled(True)

        self.progress.setValue(80)
        QApplication.processEvents()

        layer.triggerRepaint()
        self.iface.mapCanvas().refresh()

        self.progress.setValue(100)
        QApplication.processEvents()

        self._save_to_qsettings()

        QMessageBox.information(
            self, "LVT4U",
            "Đã áp dụng nhãn lô!" if self.lang == 'vi'
            else "Plot labels applied!"
        )
        self.progress.setVisible(False)
