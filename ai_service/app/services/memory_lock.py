import threading

from loguru import logger


class MemoryLockManager:
    """记忆文件编辑状态管理器"""

    def __init__(self):
        self._locks: dict[str, threading.Lock] = {}
        self._status: dict[str, str] = {}  # memory_id -> "idle" | "editing"
        self._lock = threading.Lock()  # 保护 _locks 和 _status 的锁

    def get_status(self, memory_id: str) -> str:
        """获取 memory_id 的当前编辑状态"""
        with self._lock:
            return self._status.get(memory_id, "idle")

    def acquire(self, memory_id: str) -> bool:
        """获取编辑锁，返回是否成功获取"""
        with self._lock:
            if memory_id not in self._locks:
                self._locks[memory_id] = threading.Lock()
            if memory_id not in self._status:
                self._status[memory_id] = "idle"

        lock = self._locks[memory_id]
        acquired = lock.acquire(timeout=60)  # 最多等待60秒
        if acquired:
            with self._lock:
                self._status[memory_id] = "editing"
            logger.info(f"获取编辑锁成功: {memory_id}")
        else:
            logger.warning(f"获取编辑锁超时: {memory_id}")
        return acquired

    def release(self, memory_id: str):
        """释放编辑锁"""
        with self._lock:
            self._status[memory_id] = "idle"
        if memory_id in self._locks:
            self._locks[memory_id].release()
        logger.info(f"释放编辑锁: {memory_id}")