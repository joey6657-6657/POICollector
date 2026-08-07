"""跨页 / 跨批次 POI 去重。

高德翻页或多次请求可能返回重复 POI，按唯一 id 去重。
无 id 的记录无法判定重复，默认保留。
"""


class Deduplicator:
    def __init__(self):
        self.seen = set()

    def is_new(self, poi_id):
        if poi_id is None:
            return True
        if poi_id in self.seen:
            return False
        self.seen.add(poi_id)
        return True

    def filter(self, records):
        out = []
        for r in records:
            if self.is_new(r.get("id")):
                out.append(r)
        return out

    def count(self):
        return len(self.seen)
