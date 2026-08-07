"""结果导出器：CSV / Excel(.xlsx) / GeoJSON / JSON / Shapefile 五格式。"""
import csv
import json
import os
from typing import Any, Dict, List

try:
    import shapefile  # pyshp（纯 Python 写 shapefile）
except ImportError:
    shapefile = None

# WGS-84 (EPSG:4326) 投影定义，写入 .prj 供 ArcGIS 正确识别坐标系
WGS84_PRJ = ('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
             'SPHEROID["WGS_1984",6378137,298.257223563]],'
             'PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]]')

# 导出列顺序（与 amap_client 规范化字段一致）
COLUMNS = [
    "id", "name", "type", "typecode", "address",
    "lng", "lat", "lng_wgs84", "lat_wgs84",
    "tel", "pname", "cityname", "adname", "adcode",
    "distance", "business_area", "rating", "cost",
]


class Exporter:
    def export(self, records: List[Dict[str, Any]], path: str, fmt: str):
        fmt = (fmt or "csv").lower()
        if fmt == "csv":
            self._to_csv(records, path)
        elif fmt == "json":
            self._to_json(records, path)
        elif fmt == "geojson":
            self._to_geojson(records, path)
        elif fmt in ("excel", "xlsx"):
            self._to_excel(records, path)
        elif fmt == "shapefile":
            self._to_shapefile(records, path)
        else:
            raise ValueError(f"不支持的导出格式: {fmt}")

    @staticmethod
    def _ensure_dir(path: str):
        d = os.path.dirname(os.path.abspath(path))
        os.makedirs(d, exist_ok=True)

    def _to_csv(self, records, path):
        self._ensure_dir(path)
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
            w.writeheader()
            for r in records:
                w.writerow({k: r.get(k) for k in COLUMNS})

    def _to_json(self, records, path):
        self._ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def _to_geojson(self, records, path):
        """GeoJSON 几何坐标使用 WGS-84（QGIS 标准），GCJ-02 同时保留在属性中。"""
        self._ensure_dir(path)
        features = []
        for r in records:
            lng = r.get("lng_wgs84") if r.get("lng_wgs84") is not None else r.get("lng")
            lat = r.get("lat_wgs84") if r.get("lat_wgs84") is not None else r.get("lat")
            if lng is None or lat is None:
                continue
            props = {k: r.get(k) for k in COLUMNS
                     if k not in ("lng", "lat", "lng_wgs84", "lat_wgs84")}
            props["lng_gcj02"] = r.get("lng")
            props["lat_gcj02"] = r.get("lat")
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": props,
            })
        fc = {"type": "FeatureCollection", "features": features}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fc, f, ensure_ascii=False, indent=2)

    def _to_excel(self, records, path):
        self._ensure_dir(path)
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("导出 Excel 需要 pandas，请先安装：pip install pandas openpyxl")
        df = pd.DataFrame([{k: r.get(k) for k in COLUMNS} for r in records])
        df.to_excel(path, index=False, engine="openpyxl")

    def _to_shapefile(self, records, path):
        """导出 ESRI Shapefile（点要素）：.shp/.shx/.dbf + .prj(WGS-84)。

        ArcMap 与 ArcGIS Pro 均能原生读取，是最稳的 ArcGIS 对接格式。
        几何坐标使用 WGS-84（lng_wgs84/lat_wgs84），GCJ-02 同时存入属性字段。
        """
        if shapefile is None:
            raise RuntimeError("导出 Shapefile 需要 pyshp，请先安装：pip install pyshp")
        self._ensure_dir(path)
        base = os.path.splitext(path)[0]
        w = shapefile.Writer(base, shapeType=shapefile.POINT, autoBalance=True)

        # shapefile 字段名 ≤10 字符；文本 ≤254，浮点 (size, decimal)
        fields = [
            ("NAME", "C", 254),
            ("TYPENAME", "C", 254),
            ("TYPECODE", "C", 20),
            ("ADDRESS", "C", 254),
            ("LNG", "F", 19, 8),
            ("LAT", "F", 19, 8),
            ("LNG_WGS", "F", 19, 8),
            ("LAT_WGS", "F", 19, 8),
            ("TEL", "C", 60),
            ("PROVINCE", "C", 50),
            ("CITY", "C", 50),
            ("DISTRICT", "C", 50),
            ("ADCODE", "C", 20),
            ("DISTANCE", "F", 19, 4),
            ("BIZAREA", "C", 50),
            ("RATING", "F", 19, 2),
            ("COST", "F", 19, 2),
        ]
        for spec in fields:
            name, typ = spec[0], spec[1]
            if typ == "C":
                w.field(name, "C", spec[2])
            else:
                w.field(name, "F", spec[2], spec[3])

        written = 0
        for r in records:
            lng = r.get("lng_wgs84") if r.get("lng_wgs84") is not None else r.get("lng")
            lat = r.get("lat_wgs84") if r.get("lat_wgs84") is not None else r.get("lat")
            if lng is None or lat is None:
                continue

            def fv(k):
                """健壮取浮点字段：兼容 list/dict/str/None，避免 float(list) 崩溃。"""
                v = r.get(k)
                if v is None:
                    return 0.0
                if isinstance(v, bool):  # bool 是 int 子类，需先排除
                    return float(int(v))
                if isinstance(v, (int, float)):
                    return float(v)
                if isinstance(v, str):
                    try:
                        return float(v.strip())
                    except (ValueError, AttributeError):
                        return 0.0
                # list/dict/其他类型 → 无法安全转 float，写 0 避免崩
                return 0.0

            def gs(k):
                """健壮取字符串字段：list/dict 等转为可读形式，避免 str(list) 写错 CSV。"""
                v = r.get(k)
                if v is None:
                    return ""
                if isinstance(v, str):
                    return v
                if isinstance(v, (list, tuple)):
                    return ",".join(str(x) for x in v if x is not None)
                if isinstance(v, dict):
                    return json.dumps(v, ensure_ascii=False)
                return str(v)

            w.point(float(lng), float(lat))
            w.record(
                gs("name"),
                gs("type"),
                gs("typecode"),
                gs("address"),
                fv("lng"), fv("lat"),
                float(lng), float(lat),
                gs("tel"),
                gs("pname"),
                gs("cityname"),
                gs("adname"),
                gs("adcode"),
                fv("distance"),
                gs("business_area"),
                fv("rating"),
                fv("cost"),
            )
            written += 1
        w.close()

        # 写入 WGS-84 投影文件，否则 ArcGIS 会按未知坐标系加载
        with open(base + ".prj", "w", encoding="utf-8") as f:
            f.write(WGS84_PRJ)
        return written
