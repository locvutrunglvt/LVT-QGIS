# -*- coding: utf-8 -*-
"""LVT Extent Drawing Tool - lets user draw a rectangle on the map canvas."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsWkbTypes, QgsRectangle, QgsPointXY


class LvtExtentTool(QgsMapTool):
    """Map tool that lets user draw a rectangle to define layout extent."""

    def __init__(self, canvas, callback):
        """
        Args:
            canvas: QgsMapCanvas instance.
            callback: function(QgsRectangle) called when drawing is complete.
        """
        super().__init__(canvas)
        self.callback = callback
        self.start_point = None
        self.end_point = None
        self.rubber_band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(30, 136, 229, 80))
        self.rubber_band.setStrokeColor(QColor(21, 101, 192))
        self.rubber_band.setWidth(2)
        self.setCursor(Qt.CrossCursor)

    def canvasPressEvent(self, event):
        """Start drawing rectangle."""
        self.start_point = self.toMapCoordinates(event.pos())
        self.end_point = self.start_point
        self._update_rubber_band()

    def canvasMoveEvent(self, event):
        """Update rectangle while dragging."""
        if self.start_point is None:
            return
        self.end_point = self.toMapCoordinates(event.pos())
        self._update_rubber_band()

    def canvasReleaseEvent(self, event):
        """Finish drawing and call back."""
        if self.start_point is None:
            return
        self.end_point = self.toMapCoordinates(event.pos())

        rect = QgsRectangle(self.start_point, self.end_point)
        rect.normalize()

        # Clean up
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.start_point = None
        self.end_point = None

        # Restore previous map tool
        self.canvas().unsetMapTool(self)

        # Callback with the drawn extent
        if rect.width() > 0 and rect.height() > 0:
            self.callback(rect)

    def _update_rubber_band(self):
        """Draw rectangle from start to current point."""
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        if self.start_point and self.end_point:
            p1 = self.start_point
            p2 = self.end_point
            self.rubber_band.addPoint(QgsPointXY(p1.x(), p1.y()), False)
            self.rubber_band.addPoint(QgsPointXY(p2.x(), p1.y()), False)
            self.rubber_band.addPoint(QgsPointXY(p2.x(), p2.y()), False)
            self.rubber_band.addPoint(QgsPointXY(p1.x(), p2.y()), True)

    def deactivate(self):
        """Clean up when tool is deactivated."""
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()
