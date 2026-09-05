"""离线单元测试：不访问高德、不使用真实 Key、不写入项目运行目录。"""
import csv
import json

import pytest

from poi_collector.core.amap_client import AMapClient
from poi_collector.core.checkpoint import Checkpoint
from poi_collector.core.coord_transform import gcj02_to_wgs84, wgs84_to_gcj02
from poi_collector.core.key_manager import KeyManager
from poi_collector.core.paginator import Paginator
from poi_collector.core.splitter import (
    _quad_split,
    around_bounds,
    bounds_to_polygon,
    point_in_polygon,
)
from poi_collector.data.deduplicator import Deduplicator
from poi_collector.data.exporter import Exporter


@pytest.fixture
def record():
    return {
        "id": "B000000001",
        "name": "测试 POI",
        "type": "餐饮服务",
        "typecode": "050000",
        "address": "测试路 1 号",
        "lng": 118.79,
        "lat": 32.04,
        "lng_wgs84": 118.78,
        "lat_wgs84": 32.03,
        "tel": "",
        "pname": "江苏省",
        "cityname": "南京市",
        "adname": "鼓楼区",
        "adcode": "320106",
        "distance": 100,
        "business_area": "测试商圈",
        "rating": "4.5",
        "cost": "50",
    }


def test_coordinate_round_trip_and_outside_china():
    lng, lat = 118.793, 32.047
    converted = wgs84_to_gcj02(lng, lat)
    restored = gcj02_to_wgs84(*converted)
    assert restored[0] == pytest.approx(lng, abs=1e-3)
    assert restored[1] == pytest.approx(lat, abs=1e-3)
    assert wgs84_to_gcj02(0.0, 51.5) == (0.0, 51.5)


def test_deduplicator_keeps_first_and_records_without_id():
    dedup = Deduplicator()
    records = [{"id": "A"}, {"id": "A"}, {"id": "B"}, {"id": None}]
    assert [item["id"] for item in dedup.filter(records)] == ["A", "B", None]
    assert dedup.count() == 2


@pytest.mark.parametrize(
    ("collected", "returned", "total", "page", "expected"),
    [
        (0, 20, 25, 1, True),
        (20, 5, 25, 1, False),
        (25, 20, 25, 2, False),
        (200, 20, 500, 1, False),
        (20, 20, 500, 100, False),
    ],
)
def test_paginator_stops_at_expected_boundaries(collected, returned, total, page, expected):
    paginator = Paginator(page_size=20, max_records=200, max_pages=100)
    assert paginator.should_continue(collected, returned, total, page) is expected


def test_key_manager_skips_exhausted_keys():
    manager = KeyManager(["first", "second"])
    assert manager.current() == "first"
    manager.mark_exhausted("second")
    assert manager.next_key() == "first"
    manager.mark_exhausted("first")
    assert manager.next_key() is None
    assert manager.available_count() == 0


def test_checkpoint_round_trip_and_clear(tmp_path):
    path = tmp_path / "checkpoint.json"
    checkpoint = Checkpoint(str(path))
    checkpoint.save(["A", "B"], last_page=3, params_hash="example")
    loaded = Checkpoint(str(path)).load()
    assert set(loaded["collected_ids"]) == {"A", "B"}
    assert loaded["last_page"] == 3
    assert loaded["params_hash"] == "example"
    checkpoint.clear()
    assert not path.exists()


def test_search_pagination_uses_mocked_responses_without_network():
    client = AMapClient(["not-a-real-key"], paginator=Paginator(page_size=20))
    calls = []

    def fake_call(endpoint, params, base=None):
        calls.append((endpoint, params["page"]))
        if params["page"] == 1:
            pois = [
                {"id": f"id-{i}", "name": f"POI {i}", "location": "118.79,32.04"}
                for i in range(20)
            ]
            return {"status": "1", "count": 25, "pois": pois}
        pois = [
            {"id": f"id-{i}", "name": f"POI {i}", "location": "118.79,32.04"}
            for i in range(20, 25)
        ]
        return {"status": "1", "count": 25, "pois": pois}

    client._call = fake_call
    records, total = client.search(
        "around", {"location": "118.79,32.04", "radius": 5000}, auto_paginate=True
    )
    assert total == 25
    assert len(records) == 25
    assert calls == [("/around", 1), ("/around", 2)]


def test_normalize_handles_coordinates_and_business_fields():
    client = AMapClient(["not-a-real-key"])
    poi = {
        "id": "B000", "name": "测试", "type": "餐饮", "location": "118.79,32.04",
        "address": "某路", "biz_ext": {"rating": "4.5", "cost": "50"},
    }
    normalized = client._normalize(poi)
    assert normalized["lng"] == 118.79
    assert normalized["lat"] == 32.04
    assert normalized["lng_wgs84"] is not None
    assert normalized["rating"] == "4.5"
    assert normalized["cost"] == "50"


def test_grid_geometry_helpers():
    bounds = around_bounds(120.0, 30.0, 1000)
    assert bounds[0] < 120.0 < bounds[2]
    assert bounds[1] < 30.0 < bounds[3]
    assert len(_quad_split((0, 0, 2, 2))) == 4
    polygon = bounds_to_polygon((120.0, 30.0, 121.0, 31.0))
    assert polygon.startswith("120.000000,31.000000")
    square = [(0, 0), (1, 0), (1, 1), (0, 1)]
    assert point_in_polygon(0.5, 0.5, square)
    assert not point_in_polygon(1.5, 0.5, square)


def test_poi_types_table_codes_are_six_digits():
    """回归：编码表不得缺失前导零（Excel 转换曾把 050000 削成 50000，勾类型必 0 条）。"""
    import json
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "poi_collector", "data", "poi_types.json")
    with open(path, encoding="utf-8") as f:
        types = json.load(f)
    assert len(types) == 915
    for t in types:
        assert len(t["code"]) == 6 and t["code"].isdigit(), t
    by_name = {t["name"]: t["code"] for t in types}
    assert by_name["汽车服务"] == "010000"
    assert by_name["汽车维修"] == "030000"
    assert by_name["餐饮服务"] == "050000"
    # 子类编码前两位必须与所属大类一致
    top = {name: code for name, code in by_name.items() if ">" not in name}
    for name, code in by_name.items():
        if ">" in name:
            parent = top.get(name.split(" > ")[0])
            assert parent is not None and code[:2] == parent[:2], name


def test_polygon_ring_closure_and_bbox_query_helpers():
    """大多边形降级路径：自动闭合、包围盒参数、内存边界过滤。"""
    from poi_collector.core.splitter import (
        MAX_DIRECT_POLYGON_VERTS,
        bbox_polygon_param,
        close_ring,
        filter_records_in_polygon,
        verts_to_polygon_param,
    )
    verts = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    closed = close_ring(verts)
    assert len(closed) == 5 and closed[-1] == closed[0]
    assert close_ring(closed) == closed  # 已闭合则不再追加
    assert verts_to_polygon_param(closed).count("|") == 4
    rect = bbox_polygon_param(verts)
    assert rect.startswith("0.000000,2.000000")
    assert rect.endswith("0.000000,2.000000")
    assert MAX_DIRECT_POLYGON_VERTS == 100
    records = [
        {"id": "in", "lng": 1.0, "lat": 1.0},
        {"id": "out", "lng": 3.0, "lat": 1.0},
        {"id": "nocoord", "lng": None, "lat": None},
    ]
    assert [r["id"] for r in filter_records_in_polygon(records, [verts])] == ["in"]


def test_exporter_writes_csv_json_geojson_excel_and_shapefile(tmp_path, record):
    exporter = Exporter()
    records = [record]

    csv_path = tmp_path / "result.csv"
    json_path = tmp_path / "result.json"
    geojson_path = tmp_path / "result.geojson"
    excel_path = tmp_path / "result.xlsx"
    shapefile_path = tmp_path / "result.shp"

    exporter.export(records, str(csv_path), "csv")
    exporter.export(records, str(json_path), "json")
    exporter.export(records, str(geojson_path), "geojson")
    exporter.export(records, str(excel_path), "excel")
    written = exporter._to_shapefile(records, str(shapefile_path))

    assert written == 1
    assert csv_path.exists() and json_path.exists() and geojson_path.exists() and excel_path.exists()
    assert shapefile_path.exists()
    assert shapefile_path.with_suffix(".shx").exists()
    assert shapefile_path.with_suffix(".dbf").exists()
    assert shapefile_path.with_suffix(".prj").exists()

    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        assert next(csv.DictReader(handle))["name"] == "测试 POI"
    assert json.loads(json_path.read_text(encoding="utf-8"))[0]["id"] == "B000000001"
    geojson = json.loads(geojson_path.read_text(encoding="utf-8"))
    assert geojson["features"][0]["geometry"]["coordinates"] == [118.78, 32.03]
