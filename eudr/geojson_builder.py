# -*- coding: utf-8 -*-
"""
LVT EUDR Module — GeoJSON Builder Engine.

Converts QGIS vector layer features to EUDR-compliant GeoJSON format.

Scientific basis:
    - EU Regulation 2023/1115 (EU Deforestation Regulation)
    - GeoJSON RFC 7946 (https://tools.ietf.org/html/rfc7946)
    - EPSG:4326 — WGS84 geodetic CRS

EUDR Requirements implemented:
    1. CRS must be WGS84 (EPSG:4326)
    2. Coordinates must have ≥6 decimal digits precision
    3. Plots ≤ 4 ha → single Point (centroid)
    4. Plots > 4 ha → Polygon (closed boundary)
    5. Polygons must be closed (first coord == last coord)
    6. No self-intersecting polygons
    7. Each polygon represents one single plot
    8. GeoJSON file ≤ 25 MB

Author: Lộc Vũ Trung (LVT) / Slow Forest
License: GPL-3.0
"""

import json
import math
import os

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsDistanceArea,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsWkbTypes,
)


# EUDR mandated output CRS
EUDR_CRS = QgsCoordinateReferenceSystem("EPSG:4326")

# EUDR area threshold in hectares
DEFAULT_AREA_THRESHOLD_HA = 4.0

# Minimum coordinate decimal precision required by EUDR
MIN_DECIMAL_PRECISION = 6

# Maximum file size in bytes (25 MB)
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

# Export modes
MODE_EUDR_MIXED = "eudr_mixed"       # ≤4ha→Point, >4ha→Polygon (EUDR standard)
MODE_ALL_POINTS = "all_points"        # All features → Point on Surface
MODE_ALL_POLYGONS = "all_polygons"    # All features → Polygon + lat/lon props
MODE_POINT_UNDER_4 = "point_under4"  # Only ≤4ha → Point
MODE_POLY_OVER_4 = "poly_over4"      # Only >4ha → Polygon



class EudrJsonEncoder(json.JSONEncoder):
    """Custom JSON encoder that preserves trailing zeros for coordinates.

    Ensures all float values are written with at least 6 decimal places,
    as required by EUDR geolocation precision standards.
    """

    def __init__(self, *args, precision=6, **kwargs):
        super().__init__(*args, **kwargs)
        self._precision = precision
        self._fmt = f"%.{precision}f"

    def encode(self, o):
        return self._encode_value(o)

    def _encode_value(self, o):
        if isinstance(o, float):
            return self._fmt % o
        if isinstance(o, dict):
            items = ', '.join(
                f'{json.dumps(k)}: {self._encode_value(v)}'
                for k, v in o.items()
            )
            return '{' + items + '}'
        if isinstance(o, list):
            items = ', '.join(self._encode_value(v) for v in o)
            return '[' + items + ']'
        return super().encode(o)

    def iterencode(self, o, _one_shot=False):
        yield self.encode(o)


class EudrValidationResult:
    """Container for geometry validation results."""

    def __init__(self):
        self.total_features = 0
        self.point_count = 0
        self.polygon_count = 0
        self.invalid_count = 0
        self.null_geometry_count = 0
        self.repaired_count = 0
        self.errors = []

    @property
    def valid_count(self):
        """Return count of valid features."""
        return self.point_count + self.polygon_count


class EudrGeoJsonBuilder:
    """Build EUDR-compliant GeoJSON from a QGIS vector layer.

    Handles:
        - CRS transformation to WGS84
        - Area-based geometry type selection (Point vs Polygon)
        - Geometry validation and repair
        - Field mapping to EUDR properties
        - Coordinate precision enforcement

    Args:
        layer: QgsVectorLayer source layer.
        field_mapping: dict mapping EUDR property names to source field names
                       or static values. Example:
                       {
                           "ProductionPlace": "ten_lo",
                           "Country": "__static__:VN",
                           "PlotID": "ma_lo",
                           "Area_ha": "__auto__",
                       }
        area_threshold_ha: float, plots ≤ this → Point, > this → Polygon.
        precision: int, number of decimal digits for coordinates.
        area_field: str or None, source field for area. None = auto-calculate.
        validate_geometries: bool, whether to validate and repair geometries.
    """

    # Prefix for static (manually entered) values
    STATIC_PREFIX = "__static__:"
    # Sentinel for auto-calculated area
    AUTO_AREA = "__auto__"

    def __init__(
        self,
        layer,
        field_mapping,
        area_threshold_ha=DEFAULT_AREA_THRESHOLD_HA,
        precision=MIN_DECIMAL_PRECISION,
        area_field=None,
        validate_geometries=True,
        export_mode=MODE_EUDR_MIXED,
    ):
        self.layer = layer
        self.field_mapping = field_mapping
        self.area_threshold_ha = area_threshold_ha
        self.precision = max(precision, MIN_DECIMAL_PRECISION)
        self.area_field = area_field
        self.validate_geometries = validate_geometries
        self.export_mode = export_mode

        # Setup CRS transform if needed
        self.source_crs = layer.crs()
        self.needs_transform = self.source_crs != EUDR_CRS
        if self.needs_transform:
            self.transform = QgsCoordinateTransform(
                self.source_crs, EUDR_CRS, QgsProject.instance()
            )
        else:
            self.transform = None

        # Area calculator (ellipsoidal for accuracy)
        self.area_calc = QgsDistanceArea()
        self.area_calc.setEllipsoid("WGS84")
        self.area_calc.setSourceCrs(EUDR_CRS, QgsProject.instance().transformContext())

    def preview_statistics(self):
        """Scan the layer and return validation statistics without exporting.

        Returns:
            EudrValidationResult: Statistics about the layer.
        """
        result = EudrValidationResult()
        result.total_features = self.layer.featureCount()

        for feat in self.layer.getFeatures():
            geom = feat.geometry()
            if geom is None or geom.isNull():
                result.null_geometry_count += 1
                continue

            # Transform to WGS84 for area calculation
            geom_wgs = QgsGeometry(geom)
            if self.needs_transform:
                geom_wgs.transform(self.transform)

            # Validate
            if self.validate_geometries and not geom_wgs.isGeosValid():
                repaired = geom_wgs.makeValid()
                if repaired and repaired.isGeosValid():
                    result.repaired_count += 1
                    geom_wgs = repaired
                else:
                    result.invalid_count += 1
                    result.errors.append(
                        f"Feature {feat.id()}: invalid geometry, cannot repair"
                    )
                    continue

            # Calculate area
            area_ha = self._get_area_ha(feat, geom_wgs)

            if area_ha <= self.area_threshold_ha:
                result.point_count += 1
            else:
                result.polygon_count += 1

        return result

    def build(self, output_path):
        """Build the EUDR GeoJSON file.

        Algorithm:
            1. For each feature in the source layer:
               a. Skip null geometries
               b. Transform geometry to WGS84 (EPSG:4326)
               c. Validate geometry (repair if needed)
               d. Calculate area in hectares
               e. If area ≤ threshold: use centroid Point
               f. If area > threshold: use Polygon boundary
               g. Ensure polygon is closed
               h. Round coordinates to required precision
               i. Map source fields to EUDR properties
            2. Assemble FeatureCollection
            3. Write to file

        Args:
            output_path: str, path to output .geojson file.

        Returns:
            tuple: (success: bool, message: str, result: EudrValidationResult)
        """
        result = EudrValidationResult()
        features_json = []

        for feat in self.layer.getFeatures():
            result.total_features += 1
            geom = feat.geometry()

            # Skip null geometries
            if geom is None or geom.isNull():
                result.null_geometry_count += 1
                result.errors.append(
                    f"Feature {feat.id()}: null geometry — skipped"
                )
                continue

            # Deep copy and transform to WGS84
            geom_wgs = QgsGeometry(geom)
            if self.needs_transform:
                geom_wgs.transform(self.transform)

            # Validate and repair geometry
            if self.validate_geometries:
                geom_wgs, is_valid = self._validate_and_repair(
                    geom_wgs, feat.id(), result
                )
                if not is_valid:
                    continue

            # Calculate area in hectares
            area_ha = self._get_area_ha(feat, geom_wgs)

            # Decide geometry type based on export mode
            geojson_geom = None
            skip = False

            if self.export_mode == MODE_ALL_POINTS:
                # All → Point on Surface
                geojson_geom = self._to_point_geojson(geom_wgs)
                result.point_count += 1

            elif self.export_mode == MODE_ALL_POLYGONS:
                # All → Polygon with lat/lon in properties
                geojson_geom = self._to_polygon_geojson(geom_wgs)
                result.polygon_count += 1

            elif self.export_mode == MODE_POINT_UNDER_4:
                # Only ≤ threshold → Point, skip others
                if area_ha <= self.area_threshold_ha:
                    geojson_geom = self._to_point_geojson(geom_wgs)
                    result.point_count += 1
                else:
                    skip = True

            elif self.export_mode == MODE_POLY_OVER_4:
                # Only > threshold → Polygon, skip others
                if area_ha > self.area_threshold_ha:
                    geojson_geom = self._to_polygon_geojson(geom_wgs)
                    result.polygon_count += 1
                else:
                    skip = True

            else:
                # MODE_EUDR_MIXED (default EUDR standard)
                if area_ha <= self.area_threshold_ha:
                    geojson_geom = self._to_point_geojson(geom_wgs)
                    result.point_count += 1
                else:
                    geojson_geom = self._to_polygon_geojson(geom_wgs)
                    result.polygon_count += 1

            if skip:
                continue

            if geojson_geom is None:
                result.invalid_count += 1
                result.errors.append(
                    f"Feature {feat.id()}: failed to convert geometry"
                )
                continue

            # Build properties from field mapping
            properties = self._build_properties(feat, area_ha, geom_wgs)

            # Add lat/lon to properties for polygon exports
            if geojson_geom["type"] == "Polygon":
                pos = geom_wgs.pointOnSurface()
                if pos and not pos.isNull():
                    pt = pos.asPoint()
                    properties["Latitude"] = round(pt.y(), self.precision)
                    properties["Longitude"] = round(pt.x(), self.precision)

            feature_json = {
                "type": "Feature",
                "geometry": geojson_geom,
                "properties": properties,
            }
            features_json.append(feature_json)

        # Assemble FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "features": features_json,
        }

        # Write to file
        try:
            # Use custom encoder to preserve trailing zeros
            encoder = EudrJsonEncoder(
                ensure_ascii=False, precision=self.precision
            )
            raw = encoder.encode(geojson)
            # Pretty-print with indent
            parsed = json.loads(raw)
            json_str = json.dumps(
                parsed, ensure_ascii=False, indent=2,
                allow_nan=False,
            )
            # Final pass: ensure all coordinate floats have N decimals
            import re
            def _pad_float(m):
                s = m.group(0)
                if '.' in s:
                    intpart, decpart = s.split('.')
                    if len(decpart) < self.precision:
                        decpart = decpart.ljust(self.precision, '0')
                    return intpart + '.' + decpart
                return s
            json_str = re.sub(
                r'(?<=[:\s,\[])(-?\d+\.\d+)',
                _pad_float,
                json_str,
            )

            # Check file size
            size_bytes = len(json_str.encode("utf-8"))
            if size_bytes > MAX_FILE_SIZE_BYTES:
                return (
                    False,
                    f"File size {size_bytes / (1024*1024):.1f} MB exceeds "
                    f"25 MB limit. Split into multiple files.",
                    result,
                )

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)

            return (True, output_path, result)

        except Exception as e:
            return (False, str(e), result)

    # ------------------------------------------------------------------
    # Geometry Conversion
    # ------------------------------------------------------------------

    def _to_point_geojson(self, geom_wgs):
        """Convert geometry to GeoJSON Point (point on surface).

        Uses pointOnSurface() instead of centroid() to guarantee
        the point falls inside the polygon (important for concave shapes).
        GeoJSON coordinate order: [longitude, latitude].

        Args:
            geom_wgs: QgsGeometry in WGS84.

        Returns:
            dict: GeoJSON Point geometry, or None on failure.
        """
        try:
            # pointOnSurface is always inside the polygon
            pos = geom_wgs.pointOnSurface()
            if pos is None or pos.isNull():
                # Fallback to centroid
                pos = geom_wgs.centroid()
            if pos is None or pos.isNull():
                return None
            pt = pos.asPoint()
            return {
                "type": "Point",
                "coordinates": [
                    round(pt.x(), self.precision),  # longitude
                    round(pt.y(), self.precision),  # latitude
                ],
            }
        except Exception:
            return None

    def _to_polygon_geojson(self, geom_wgs):
        """Convert geometry to GeoJSON Polygon.

        Handles:
            - MultiPolygon → extracts largest polygon
            - Ensures polygon is closed (first == last coordinate)
            - GeoJSON coordinate order: [longitude, latitude]

        Args:
            geom_wgs: QgsGeometry in WGS84.

        Returns:
            dict: GeoJSON Polygon geometry, or None on failure.
        """
        try:
            # Handle MultiPolygon: use the largest polygon
            wkb_type = QgsWkbTypes.flatType(geom_wgs.wkbType())

            if wkb_type == QgsWkbTypes.MultiPolygon:
                multi = geom_wgs.asMultiPolygon()
                if not multi:
                    return None
                # Find the largest polygon by number of vertices
                largest = max(multi, key=lambda rings: sum(len(r) for r in rings))
                rings = largest
            elif wkb_type == QgsWkbTypes.Polygon:
                rings = geom_wgs.asPolygon()
            else:
                # Not a polygon type — try to convert to polygon
                return None

            if not rings:
                return None

            geojson_rings = []
            for ring in rings:
                coords = [
                    [round(pt.x(), self.precision), round(pt.y(), self.precision)]
                    for pt in ring
                ]
                # Ensure polygon is closed (EUDR requirement)
                if coords and coords[0] != coords[-1]:
                    coords.append(coords[0])
                geojson_rings.append(coords)

            return {
                "type": "Polygon",
                "coordinates": geojson_rings,
            }

        except Exception:
            return None

    # ------------------------------------------------------------------
    # Geometry Validation
    # ------------------------------------------------------------------

    def _validate_and_repair(self, geom_wgs, fid, result):
        """Validate geometry and attempt repair if invalid.

        Checks:
            - GEOS validity (no self-intersection, proper closure)
            - Attempts makeValid() for invalid geometries

        Args:
            geom_wgs: QgsGeometry in WGS84.
            fid: Feature ID for error reporting.
            result: EudrValidationResult to accumulate stats.

        Returns:
            tuple: (repaired_geom, is_valid)
        """
        if geom_wgs.isGeosValid():
            return geom_wgs, True

        # Attempt repair
        repaired = geom_wgs.makeValid()
        if repaired is not None and not repaired.isNull() and repaired.isGeosValid():
            result.repaired_count += 1
            result.errors.append(
                f"Feature {fid}: geometry repaired (self-intersection or unclosed)"
            )
            return repaired, True

        # Repair failed
        result.invalid_count += 1
        result.errors.append(
            f"Feature {fid}: invalid geometry, repair failed — skipped"
        )
        return geom_wgs, False

    # ------------------------------------------------------------------
    # Area Calculation
    # ------------------------------------------------------------------

    def _get_area_ha(self, feat, geom_wgs):
        """Calculate or retrieve the area of a feature in hectares.

        Two modes:
            1. Auto-calculate from geometry (ellipsoidal, accurate)
            2. Read from a specified source field

        Args:
            feat: QgsFeature.
            geom_wgs: QgsGeometry in WGS84.

        Returns:
            float: Area in hectares.
        """
        if self.area_field and self.area_field != self.AUTO_AREA:
            # Read from field
            try:
                val = feat[self.area_field]
                if val is not None:
                    return float(val)
            except (ValueError, TypeError, KeyError):
                pass

        # Auto-calculate from geometry (ellipsoidal)
        try:
            area_sqm = self.area_calc.measureArea(geom_wgs)
            # Convert to hectares (1 ha = 10,000 m²)
            return area_sqm / 10000.0
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Property Mapping
    # ------------------------------------------------------------------

    def _build_properties(self, feat, area_ha, geom_wgs=None):
        """Map source feature fields to EUDR GeoJSON properties.

        The field_mapping dict supports:
            - Direct field reference: "eudr_name": "source_field_name"
            - Static value: "eudr_name": "__static__:value"
            - Auto area: "Area_ha": "__auto__"
            - Auto lat/lon: "Latitude"/"Longitude": "__auto__"

        Args:
            feat: QgsFeature.
            area_ha: float, calculated area in hectares.
            geom_wgs: QgsGeometry in WGS84 (for Lat/Lon calculation).

        Returns:
            dict: EUDR properties.
        """
        props = {}
        field_names = [f.name() for f in feat.fields()]

        for eudr_key, source_ref in self.field_mapping.items():
            if not source_ref:
                continue

            if source_ref == self.AUTO_AREA:
                if eudr_key == "Area_ha":
                    props[eudr_key] = round(area_ha, 4)
                elif eudr_key in ("Latitude", "Longitude") and geom_wgs:
                    # Auto Lat/Lon from Point on Surface
                    pos = geom_wgs.pointOnSurface()
                    if pos and not pos.isNull():
                        pt = pos.asPoint()
                        if eudr_key == "Latitude":
                            props[eudr_key] = round(pt.y(), self.precision)
                        else:
                            props[eudr_key] = round(pt.x(), self.precision)
                else:
                    props[eudr_key] = round(area_ha, 4)
            elif source_ref.startswith(self.STATIC_PREFIX):
                # Static value
                props[eudr_key] = source_ref[len(self.STATIC_PREFIX):]
            elif source_ref in field_names:
                # Source field reference — sanitize QVariant to Python
                val = feat[source_ref]
                props[eudr_key] = self._to_python(val)
            else:
                # Field not found — store as static text
                props[eudr_key] = source_ref

        # Always include area
        if "Area_ha" not in props:
            props["Area_ha"] = round(area_ha, 4)

        return props

    @staticmethod
    def _to_python(val):
        """Convert a QVariant / QGIS field value to a JSON-safe Python type."""
        if val is None:
            return None
        # QVariant NULL check (PyQt5 wraps NULL as QPyNullVariant)
        try:
            if not val and not isinstance(val, (int, float, str, bool)):
                return None
        except TypeError:
            return None
        if isinstance(val, (int, float, str, bool)):
            if isinstance(val, float) and math.isnan(val):
                return None
            return val
        # Fallback: convert to string
        return str(val)
