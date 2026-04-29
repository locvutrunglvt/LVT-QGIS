# -*- coding: utf-8 -*-
"""LVT Map Layout - Engine: template loading, layout creation.

Design principle: templates are SELF-CONTAINED.  They handle ALL
positioning, grids, and frames via data-defined expressions.
This engine only:
  1. Loads the template
  2. Sets page size
  3. Sets map extent & scale
  4. Refreshes until expressions converge
  5. Updates user-provided labels
  6. Toggles element visibility per user checkboxes
"""

import os

from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProject,
    QgsPrintLayout,
    QgsReadWriteContext,
    QgsLayoutItemMap,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemPicture,
    QgsLayoutSize,
    QgsUnitTypes,
)


# Template file mapping: (mode, lang) → filename
TEMPLATES = {
    ("slide", "EN"): "Khung_Slide_EN.qpt",
    ("slide", "VN"): "Khung_Slide.qpt",
    ("print", "EN"): "Khung LVT2601_print_27Apr2026_EN.qpt",
    ("print", "VN"): "Khung LVT2601_print_27Apr2026_VN.qpt",
}

# Element IDs that the engine may update (labels, scalebars, coords).
# These are the ONLY template items the plugin touches — everything
# else (grids, frames, positions) is left to the template.
ITEM_IDS = {
    ("slide", "EN"): {
        "map": "Map",
        "map_data": "Map data",
        "scalebar_m": "Scale meter",
    },
    ("slide", "VN"): {
        "map": "Map",
        "map_data": "Dữ liệu bản đồ",
        "scalebar_m": "Scale mét",
    },
    ("print", "EN"): {
        "map": "Map",
        "title": "Map title",
        "org_name": "Map org name",
        "study_area": "Study area",
        "map_data": "Map data",
        "references": "References",
        "page_size": "Print page size",
        "scalebar_m": "Scale meter",
        "scalebar_deg": "Scalebar deg min",
        "main_frame": "Main frame",
    },
    ("print", "VN"): {
        "map": "Map",
        "title": "Tên bản đồ",
        "org_name": "Tên đv xd bản đồ",
        "study_area": "Khu vực bản đồ",
        "map_data": "Dữ liệu bản đồ",
        "references": "Viện dẫn",
        "page_size": "Kích thước trang in",
        "scalebar_m": "Scale mét",
        "scalebar_deg": "Scalebar độ phút",
        "main_frame": "Khung tổng",
    },
}


class LvtEngine:
    """Core engine: loads .qpt templates, builds layouts."""

    def __init__(self, iface, plugin_dir):
        self.iface = iface
        self.plugin_dir = plugin_dir
        self._layout_counter = 0
        self._tpl_cache = {}  # (mode, lang) → XML string

    # ── Template Resolution ──────────────────────────────────────

    def _resolve_template(self, mode, lang):
        """Find the .qpt template file."""
        fname = TEMPLATES[(mode, lang)]
        p = os.path.join(self.plugin_dir, "templates", fname)
        if os.path.exists(p):
            return p
        p = os.path.join(os.path.dirname(self.plugin_dir), fname)
        if os.path.exists(p):
            return p
        raise FileNotFoundError(
            f"Template not found: {fname}\n"
            f"Place it in: {os.path.join(self.plugin_dir, 'templates')}"
        )

    def _load_template_doc(self, mode, lang):
        """Load and cache template XML as QDomDocument."""
        key = (mode, lang)
        if key not in self._tpl_cache:
            tpl_path = self._resolve_template(mode, lang)
            with open(tpl_path, "r", encoding="utf-8") as f:
                self._tpl_cache[key] = f.read()

        doc = QDomDocument()
        ok, err_msg, err_line, _col = doc.setContent(self._tpl_cache[key])
        if not ok:
            raise RuntimeError(
                f"Template XML error at line {err_line}: {err_msg}"
            )
        return doc

    # ── Layout Creation ──────────────────────────────────────────

    def create_layout(self, params, progress_cb=None):
        """Create a QgsPrintLayout from template + user params.

        Args:
            params: Dict of layout parameters from dialog.
            progress_cb: Optional callback(step, message) for progress updates.

        Pipeline (optimized):
          1. Load template
          2. Set page size + extent + scale (batch, no refresh yet)
          3. Multi-refresh for DD convergence (2 for slide, 3 for print)
          4. Re-enforce scale + single settle refresh
          5. Update labels + toggle visibility (no refresh needed)
        """
        def _progress(step, msg):
            if progress_cb:
                progress_cb(step, msg)

        project = QgsProject.instance()
        mode = params["mode"]   # "slide" or "print"
        lang = params["lang"]   # "EN" or "VN"
        tpl_key = (mode, lang)
        ids = ITEM_IDS[tpl_key]

        # Load cached template XML
        _progress(1, "Loading template...")
        doc = self._load_template_doc(mode, lang)

        # Create layout
        self._layout_counter += 1
        layout_name = f"LVT_{mode}_{lang}_{self._layout_counter}"
        layout = QgsPrintLayout(project)

        _progress(2, "Applying template design...")
        _items, ok2 = layout.loadFromTemplate(doc, QgsReadWriteContext())
        if not ok2:
            raise RuntimeError("Failed to load template into layout.")

        layout.setName(layout_name)
        project.layoutManager().addLayout(layout)
        layout = project.layoutManager().layoutByName(layout_name)

        # ── Step 1: Batch setup (page + extent + scale) ───────────
        _progress(3, "Setting page size & map extent...")
        pw = params["page_width"]
        ph = params["page_height"]
        page = layout.pageCollection().page(0)
        page.setPageSize(
            QgsLayoutSize(pw, ph, QgsUnitTypes.LayoutMillimeters)
        )

        map_item = self._find_item(layout, ids["map"], QgsLayoutItemMap)
        if map_item:
            extent = self._resolve_extent(params)
            map_item.zoomToExtent(extent)
            map_item.setScale(params["scale"])

        # ── Step 2: Multi-refresh for DD convergence ──────────────
        cycles = 3 if mode == "print" else 2
        for i in range(cycles):
            _progress(4 + i, f"Rendering layout (pass {i+1}/{cycles})...")
            layout.refresh()
            QCoreApplication.processEvents()

        # ── Step 3: Re-enforce scale + settle ─────────────────────
        _progress(4 + cycles, "Finalizing scale...")
        if map_item:
            map_item.setScale(params["scale"])
            layout.refresh()
            QCoreApplication.processEvents()

        # ── Step 4: Update labels ─────────────────────────────────
        _progress(5 + cycles, "Writing labels...")
        self._update_labels(layout, ids, params)

        # ── Step 5: Toggle element visibility ─────────────────────
        _progress(6 + cycles, "Configuring elements...")
        if not params["show_scalebar"]:
            self._hide_item(layout, ids["scalebar_m"])
            if "scalebar_deg" in ids:
                self._hide_item(layout, ids["scalebar_deg"])

        if not params["show_legend"]:
            for item in layout.items():
                if isinstance(item, QgsLayoutItemLegend):
                    item.setVisibility(False)

        if not params["show_north"]:
            for item in layout.items():
                if isinstance(item, QgsLayoutItemPicture):
                    item.setVisibility(False)
        else:
            # Apply selected north arrow style
            svg_path = params.get("north_arrow_svg", "")
            if svg_path and os.path.isfile(svg_path):
                for item in layout.items():
                    if isinstance(item, QgsLayoutItemPicture):
                        item.setPicturePath(svg_path)

        # ── Final: re-enforce scale (lightweight, no full refresh) ──
        if map_item:
            map_item.setScale(params["scale"])

        _progress(7 + cycles, "Done!")
        return layout

    # ── Label Updates ─────────────────────────────────────────────

    def _update_labels(self, layout, ids, params):
        """Write user-provided text into template label items."""
        # Title
        if "title" in ids and params.get("title"):
            self._set_label(layout, ids["title"], params["title"])

        # Organization name
        if "org_name" in ids and params.get("org_name"):
            self._set_label(layout, ids["org_name"], params["org_name"])

        # Study area
        if "study_area" in ids and params.get("study_area"):
            self._set_label(layout, ids["study_area"], params["study_area"])

        # Data sources
        if "map_data" in ids and params.get("data_sources"):
            self._set_label(layout, ids["map_data"], params["data_sources"])

        # References / Viện dẫn: ALWAYS restore fixed title text
        if "references" in ids:
            fixed_ref = ("Dữ liệu xây dựng bản đồ:"
                         if params.get("lang") == "VN"
                         else "Map data references:")
            self._set_label(layout, ids["references"], fixed_ref)

    # ── Extent Resolution ────────────────────────────────────────

    def _resolve_extent(self, params):
        """Get the map extent based on user selection."""
        mode = params["extent_mode"]
        if mode == "drawn" and params.get("drawn_extent"):
            return params["drawn_extent"]
        elif mode == "layer" and params.get("extent_layer"):
            return params["extent_layer"].extent()
        else:
            return self.iface.mapCanvas().extent()

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _find_item(layout, item_id, item_type=None):
        item = layout.itemById(item_id)
        if item and item_type and not isinstance(item, item_type):
            return None
        return item

    @staticmethod
    def _set_label(layout, item_id, text):
        item = layout.itemById(item_id)
        if item and isinstance(item, QgsLayoutItemLabel):
            item.setText(text)

    @staticmethod
    def _hide_item(layout, item_id):
        item = layout.itemById(item_id)
        if item:
            item.setVisibility(False)
