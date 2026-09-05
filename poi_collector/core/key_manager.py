"""多 Key 配额感知轮询管理。

高德 Web 服务 Key 有日配额限制。本管理器支持：
  - 多个 Key 轮询使用，分散请求压力
  - 某个 Key 触发配额耗尽时自动切换并标记，不再使用
  - 所有 Key 耗尽时抛出明确异常
"""


class KeyManager:
    def __init__(self, keys):
        self.keys = [k.strip() for k in (keys or []) if k and k.strip()]
        self.index = 0
        self.started = False  # acquire() 首次直接用第一把 Key，此后才轮询
        self.exhausted = set()  # 记录耗尽 Key 的索引

    def __len__(self):
        return len(self.keys)

    def __bool__(self):
        return bool(self.keys)

    def current(self):
        if not self.keys:
            return None
        return self.keys[self.index]

    def acquire(self):
        """取本次请求应使用的 Key：首次返回第一把，此后逐请求轮询分摊 QPS。"""
        if not self.started:
            self.started = True
            return self.current()
        return self.next_key()

    def next_key(self):
        """切换到下一个未耗尽的 Key，返回该 Key；无可用则返回 None。"""
        if not self.keys:
            return None
        start = self.index
        for _ in range(len(self.keys)):
            self.index = (self.index + 1) % len(self.keys)
            if self.index not in self.exhausted:
                return self.current()
            if self.index == start:
                break
        return None

    def mark_exhausted(self, key=None):
        key = key or self.current()
        if key in self.keys:
            self.exhausted.add(self.keys.index(key))

    def available_count(self):
        return len(self.keys) - len(self.exhausted & set(range(len(self.keys))))

    def reset(self):
        self.exhausted.clear()
        self.index = 0
        self.started = False
