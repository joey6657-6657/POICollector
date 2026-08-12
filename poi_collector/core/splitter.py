"""区域网格分片采集：突破高德"同参数最多 200 条"的返回限制。

社区主流做法（参考 GaoDe-poi-crawler 四叉树 / POIKit 网格四分）：
  1. 把搜索区域（around 的圆 / polygon 的多边形）用包围盒网格化
  2. 对每个子网格发一次"探测"请求，读 count（该区域真实 POI 总数）
  3. count < 阈值 → 直接翻页采集该子网格全部 POI
  4. count >= 阈值 → 递归四分该子网格，直到每个网格都装得下
  5. 所有子网格结果经同一个去重器合并，再按原始范围过滤（圆内/多边形内）

配合多 Key 轮询（KeyManager），即可同时解决：
  - 200 条/次 返回上限（分片）
  - QPS/配额 限流（多 Key + 退避）
"""
import math
import time

from ..data.deduplicator import Deduplicator

# 最小网格边长（度）：约 0.0005° ≈ 50m，防止极端情况下无限递归
_GRID_MIN_SIDE_DEG = 0.0005
# 单次翻页条数（高德单页上限 25）
_PAGE_SIZE = 25


# ---------------------------------------------------------------------- #
# 几何工具
# ---------------------------------------------------------------------- #
def meters_to_deg_offsets(lng, lat, radius_m):
    """把半径（米）换算为经纬度偏移。

    纬度方向：1° ≈ 111,320 m（固定）
    经度方向：1° ≈ 111,320 × cos(lat) m（随纬度收缩）
    返回 (经度偏移, 纬度偏移)
    """
    dlat = radius_m / 111320.0
    dlng = radius_m / (111320.0 * max(math.cos(math.radians(lat)), 0.01))
    return dlng, dlat


def around_bounds(lng, lat, radius_m):
    """周边搜索的中心点+半径 → 覆盖该圆的包围盒。

    返回 (min_lng, min_lat, max_lng, max_lat)。
    圆的外接正方形，保证任何距离中心 ≤ radius 的点都在盒内。
    """
    dlng, dlat = meters_to_deg_offsets(lng, lat, radius_m)
    return lng - dlng, lat - dlat, lng + dlng, lat + dlat


def polygon_bounds(vertices):
    """用户多边形 → 包围盒 (min_lng, min_lat, max_lng, max_lat)。"""
    lngs = [p[0] for p in vertices]
    lats = [p[1] for p in vertices]
    return min(lngs), min(lats), max(lngs), max(lats)


def bounds_to_polygon(bounds):
    """包围盒 → 高德 polygon 参数（矩形，4 顶点闭合，| 分隔）。"""
    min_lng, min_lat, max_lng, max_lat = bounds
    return (f"{min_lng:.6f},{max_lat:.6f}|{max_lng:.6f},{max_lat:.6f}|"
            f"{max_lng:.6f},{min_lat:.6f}|{min_lng:.6f},{min_lat:.6f}|"
            f"{min_lng:.6f},{max_lat:.6f}")


def haversine_m(lng1, lat1, lng2, lat2):
    """两经纬度点的大圆距离（米）。"""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def point_in_polygon(lng, lat, poly):
    """射线法判断点 (lng,lat) 是否在多边形 poly 内（含边界）。"""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > lat) != (yj > lat)) and \
                (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _quad_split(bounds):
    """把包围盒均分为 4 个子盒。"""
    min_lng, min_lat, max_lng, max_lat = bounds
    mid_lng = (min_lng + max_lng) / 2.0
    mid_lat = (min_lat + max_lat) / 2.0
    return [
        (min_lng, mid_lat, mid_lng, max_lat),  # 左上
        (mid_lng, mid_lat, max_lng, max_lat),  # 右上
        (min_lng, min_lat, mid_lng, mid_lat),  # 左下
        (mid_lng, min_lat, max_lng, mid_lat),  # 右下
    ]


# ---------------------------------------------------------------------- #
# 分片采集器
# ---------------------------------------------------------------------- #
class SplitCollector:
    """网格分片采集器。

    用法：
        collector = SplitCollector(
            client, mode="around", center=(lng, lat), radius=50000,
            threshold=150, max_depth=5,
            extra_params={"types": "050000"},       # 业务参数（无 polygon/location）
            progress_callback=fn, cancelled=lambda: False)
        records, total = collector.run()

    返回的 records 已去重并按原始范围过滤（圆内 / 多边形内）。
    """

    def __init__(self, client, mode="around", center=None, radius=None,
                 polygon=None, threshold=150, max_depth=5,
                 extra_params=None, progress_callback=None, cancelled=None,
                 filter_rings=None):
        self.client = client
        self.mode = mode
        self.center = center              # (lng, lat)，around 模式
        self.radius = radius              # 米，around 模式
        self.polygon = polygon            # [(lng,lat),...]，polygon 模式（用于包围盒）
        # 结果过滤环列表：None 时用 polygon 单环；关键词分片传入城市边界多环
        self.filter_rings = filter_rings
        # 阈值：50~180（留余量，避免恰好 200 时翻页不稳）
        self.threshold = max(50, min(int(threshold or 150), 180))
        self.max_depth = max(1, int(max_depth or 5))
        self.extra_params = dict(extra_params or {})
        self.progress_callback = progress_callback  # fn(current, estimate, page)
        self.cancelled = cancelled        # fn()->bool

        self._dedup = Deduplicator()
        self._records: list = []
        self._total_estimate = 0
        self._probe_count = 0  # 探测请求数（供日志）

    # ---------------- 底层请求 ---------------- #
    def _request(self, bounds, page, offset):
        """请求一个子网格的指定页，返回 (规范化 pois, count)。"""
        p = dict(self.extra_params)
        p["polygon"] = bounds_to_polygon(bounds)
        p["page"] = page
        p["offset"] = offset
        p.setdefault("extensions", "base")
        data = self.client._call("/polygon", p)
        raw_pois = data.get("pois") or []
        # 必须规范化（否则缺少 lng/lat 等字段，导出/过滤都会出错）
        normalized = [self.client._normalize(poi) for poi in raw_pois]
        return normalized, int(data.get("count") or 0)

    def _probe(self, bounds):
        """探测子网格真实 POI 总数（最小代价请求）。

        注意：异常不吞掉——若所有 Key 均被限流/配额耗尽，应终止采集
        并提示用户（静默返回 0 会导致子网格被误判为"无数据"而漏采）。
        """
        self._probe_count += 1
        _, count = self._request(bounds, 1, 1)
        return count

    def _collect_area(self, bounds):
        """采集一个子网格（count 已知 < 阈值）：翻页 + 全局去重。"""
        page = 1
        while True:
            if self.cancelled and self.cancelled():
                return
            records, _ = self._request(bounds, page, _PAGE_SIZE)
            new_records = self._dedup.filter(records)
            self._records.extend(new_records)
            if self.progress_callback:
                self.progress_callback(
                    len(self._records), self._total_estimate, page)
            # 本页未装满或已到 200 上限 → 该子网格完成
            if len(records) < _PAGE_SIZE:
                return
            page += 1
            time.sleep(0.2)  # 礼貌性间隔，降低限频风险

    # ---------------- 递归分片 ---------------- #
    def _split(self, bounds, depth):
        if self.cancelled and self.cancelled():
            return
        count = self._probe(bounds)
        if count < self.threshold or depth >= self.max_depth:
            self._collect_area(bounds)
            return
        # 网格已到最小边长 → 直接采（即便超阈值也只取前 200）
        if (bounds[2] - bounds[0]) < _GRID_MIN_SIDE_DEG or \
                (bounds[3] - bounds[1]) < _GRID_MIN_SIDE_DEG:
            self._collect_area(bounds)
            return
        for sub in _quad_split(bounds):
            if self.cancelled and self.cancelled():
                return
            self._split(sub, depth + 1)

    # ---------------- 入口 ---------------- #
    def run(self):
        if self.mode == "around" and self.center and self.radius:
            lng, lat = self.center
            root = around_bounds(lng, lat, self.radius)
        elif self.mode == "polygon" and self.polygon:
            root = polygon_bounds(self.polygon)
        else:
            raise ValueError("分片采集需要有效的中心点+半径（around）或多边形（polygon）")

        # 先探测根区域
        root_count = self._probe(root)
        self._total_estimate = root_count
        if root_count < self.threshold:
            # 整体装得下，不拆
            self._collect_area(root)
        else:
            self._split(root, 0)

        # 按原始范围过滤（around → 圆内；polygon → 多边形内）
        kept = []
        if self.mode == "around" and self.center:
            clng, clat = self.center
            for r in self._records:
                rlng, rlat = r.get("lng"), r.get("lat")
                if rlng is None or rlat is None:
                    continue
                # 1.02 容差：外接正方形边缘的 POI 因度-米换算误差
                if haversine_m(rlng, rlat, clng, clat) <= self.radius * 1.02:
                    kept.append(r)
        elif self.mode == "polygon" and self.polygon:
            # 多环边界（如城市行政区）：落在任一环内即保留
            rings = self.filter_rings if self.filter_rings else [self.polygon]
            for r in self._records:
                rlng, rlat = r.get("lng"), r.get("lat")
                if rlng is None or rlat is None:
                    continue
                if any(point_in_polygon(rlng, rlat, ring) for ring in rings):
                    kept.append(r)
        else:
            kept = self._records

        return kept, len(kept), self._probe_count
