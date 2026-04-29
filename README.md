# LVT Plugin Suite

A comprehensive QGIS plugin suite for forestry, land management, and EUDR compliance.

**Author:** Lộc Vũ Trung (LVT) / Slow Forest  
**License:** GPL-3.0  
**QGIS:** 3.28+

## Modules

| # | Module | Description | Status |
|---|--------|-------------|--------|
| 1 | Map Layout | Map layout builder | 🔄 Migration |
| 2 | KML | SHP ↔ KML/KMZ conversion | 🔄 Migration |
| 3 | MBTiles | MBTiles generator | 📋 Planned |
| 4 | GeoJSON EUDR | EU 2023/1115 GeoJSON exporter | 📋 Planned |
| 5 | Thematic Map | TT 16/2023 thematic mapping | 📋 Planned |
| 6 | Basemap | Google Maps / Satellite / Hybrid | ✅ Done |
| 7 | Legal Documents | Vietnamese forestry standards catalog | 📋 Planned |
| 8 | Font Converter | TCVN3 / VNI / Unicode / ANSI | 📋 Planned |
| 9 | CRS Tools | VN-2000 coordinate system utilities | 📋 Planned |
| 10 | Map Packager | Project packaging (Folder / GeoPackage) | 📋 Planned |
| 11 | About | Author info & language settings | ✅ Done |

## Installation (Development)

```powershell
# Create junction link (no admin required)
cmd /c mklink /J "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\LVT" "path\to\this\repo"
```

Then in QGIS: **Plugin Manager → Enable "LVT"**

## Scientific Basis

All code is 100% original, built from:
- Cartographic science and map projection mathematics
- OGC Standards (KML 2.2, GeoJSON RFC 7946, GeoPackage 1.3)
- Vietnamese technical standards (TCVN, VN-2000)
- EU Regulation 2023/1115 (EUDR)
- QGIS official API documentation
