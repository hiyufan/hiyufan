"""登录防暴力破解：同一账号 10 分钟内连续输错 5 次，锁定 10 分钟。

单进程部署，状态放在内存即可；多进程部署时应换成 Redis 等共享存储。
"""
import time
from collections import defaultdict, deque
from threading import Lock

from app.core.exceptions import BizError

MAX_FAILURES = 5
WINDOW_SECONDS = 10 * 60
LOCK_SECONDS = 10 * 60


class LoginGuard:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._locked_until: dict[str, float] = {}
        self._lock = Lock()

    def check(self, username: str) -> None:
        """登录前调用：账号处于锁定期则直接拒绝（不再校验密码，避免继续试探）。"""
        with self._lock:
            until = self._locked_until.get(username, 0)
            remaining = until - self._clock()
            if remaining > 0:
                minutes = int(remaining // 60) + 1
                raise BizError(f"密码错误次数过多，账号已锁定，请 {minutes} 分钟后再试", 429)

    def fail(self, username: str) -> int:
        """记录一次失败，返回剩余可尝试次数（0 表示刚被锁定）。"""
        now = self._clock()
        with self._lock:
            q = self._failures[username]
            q.append(now)
            while q and now - q[0] > WINDOW_SECONDS:
                q.popleft()
            if len(q) >= MAX_FAILURES:
                self._locked_until[username] = now + LOCK_SECONDS
                q.clear()
                return 0
            return MAX_FAILURES - len(q)

    def succeed(self, username: str) -> None:
        with self._lock:
            self._failures.pop(username, None)
            self._locked_until.pop(username, None)


login_guard = LoginGuard()
