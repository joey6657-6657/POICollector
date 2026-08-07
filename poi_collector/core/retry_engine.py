"""指数退避智能重试策略。

对网络抖动、限频类瞬时错误进行有限次重试，每次间隔按
base_delay * backoff_factor^attempt 增长并附带随机抖动，
避免多个客户端同时重试造成"重试风暴"。
"""
import random
import time


class RetryEngine:
    def __init__(self, max_retries=5, base_delay=1.0,
                 max_delay=30.0, backoff_factor=2.0, jitter=0.5):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def backoff_seconds(self, attempt: int) -> float:
        """第 attempt 次重试前的等待秒数（含抖动）。attempt 从 0 开始。"""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay += random.uniform(0, self.jitter)
        return delay

    def sleep(self, attempt: int):
        time.sleep(self.backoff_seconds(attempt))
