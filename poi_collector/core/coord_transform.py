"""坐标系转换工具。

高德返回的坐标为 GCJ-02（火星坐标系）。本模块提供：
  - GCJ-02  <->  WGS-84（GPS 通用）
  - GCJ-02  <->  BD-09（百度）
  - WGS-84  <->  BD-09
海外坐标不在中国加密范围内，直接原样返回。
"""
import math

_A = 6378245.0                     # 长半轴
_EE = 0.00669342162296594323       # 偏心率平方


def _out_of_china(lng: float, lat: float) -> bool:
    return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)


def _transform_lat(lng: float, lat: float) -> float:
    ret = (-100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat
           + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng)))
    ret += (20.0 * math.sin(6.0 * lng * math.pi)
            + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi)
            + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi)
            + 320.0 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(lng: float, lat: float) -> float:
    ret = (300.0 + lng + 2.0 * lat + 0.1 * lng * lng
           + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng)))
    ret += (20.0 * math.sin(6.0 * lng * math.pi)
            + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * math.pi)
            + 40.0 * math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * math.pi)
            + 300.0 * math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lng: float, lat: float):
    """WGS-84 -> GCJ-02。"""
    if _out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - _EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (_A / sqrtmagic * math.cos(radlat) * math.pi)
    return lng + dlng, lat + dlat


def gcj02_to_wgs84(lng: float, lat: float):
    """GCJ-02 -> WGS-84（高德坐标转 GPS）。"""
    if _out_of_china(lng, lat):
        return lng, lat
    glng, glat = wgs84_to_gcj02(lng, lat)
    return lng * 2 - glng, lat * 2 - glat


def gcj02_to_bd09(lng: float, lat: float):
    """GCJ-02 -> BD-09（百度）。"""
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * math.pi)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * math.pi)
    return z * math.cos(theta) + 0.0065, z * math.sin(theta) + 0.006


def bd09_to_gcj02(lng: float, lat: float):
    """BD-09 -> GCJ-02。"""
    x = lng - 0.0065
    y = lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * math.pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * math.pi)
    return z * math.cos(theta), z * math.sin(theta)


def bd09_to_wgs84(lng: float, lat: float):
    g_lng, g_lat = bd09_to_gcj02(lng, lat)
    return gcj02_to_wgs84(g_lng, g_lat)


def wgs84_to_bd09(lng: float, lat: float):
    g_lng, g_lat = wgs84_to_gcj02(lng, lat)
    return gcj02_to_bd09(g_lng, g_lat)
