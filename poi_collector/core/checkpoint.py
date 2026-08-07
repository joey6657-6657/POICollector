"""断点续爬检查点。

将已采集的 POI id、最后完成页、参数指纹序列化到磁盘，
中断后可据此跳过已采集部分继续采集。
"""
import json
import os


class Checkpoint:
    def __init__(self, path: str):
        self.path = path
        self.data = {
            "collected_ids": [],
            "last_page": 0,
            "params_hash": "",
        }

    def save(self, collected_ids, last_page: int, params_hash: str = ""):
        self.data = {
            "collected_ids": list(collected_ids),
            "last_page": last_page,
            "params_hash": params_hash,
        }
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False)
        os.replace(tmp, self.path)  # 原子写入，避免半截文件

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (ValueError, OSError):
                self.data = {"collected_ids": [], "last_page": 0, "params_hash": ""}
        return self.data

    def clear(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        self.data = {"collected_ids": [], "last_page": 0, "params_hash": ""}

    @property
    def collected_ids(self):
        return set(self.data.get("collected_ids", []))

    @property
    def last_page(self):
        return self.data.get("last_page", 0)

    @property
    def params_hash(self):
        return self.data.get("params_hash", "")
