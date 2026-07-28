import time
import threading
from loguru import logger


class ConversationMemory:
    """对话记忆管理器 - 短期 + 长期，带遗忘机制"""

    def __init__(self, max_short_term: int = 20, decay_days: int = 7):
        """
        max_short_term: 短期记忆最大条数
        decay_days: 长期记忆衰减天数阈值
        """
        self.short_term: dict[str, list] = {}
        self.long_term: dict[str, list] = {}
        self.max_short_term = max_short_term
        self.decay_days = decay_days
        self._lock = threading.Lock()

    def add_message(self, session_id: str, user_id: str, role_id: str, role: str, content: str):
        """添加消息到短期记忆"""
        with self._lock:
            if session_id not in self.short_term:
                self.short_term[session_id] = []

            self.short_term[session_id].append({
                "role": role,
                "content": content,
                "timestamp": time.time(),
            })

            if len(self.short_term[session_id]) > self.max_short_term:
                self.short_term[session_id] = self.short_term[session_id][-self.max_short_term:]

        logger.debug(f"短期记忆已添加: session={session_id}, role={role}")

    def get_short_term(self, session_id: str) -> list:
        """获取短期对话记忆"""
        with self._lock:
            return self.short_term.get(session_id, [])

    def should_convert_to_long_term(self, session_id: str) -> tuple:
        """
        判断是否需要将短期记忆转化为长期记忆
        返回 (should_convert, summary)
        """
        short_term = self.get_short_term(session_id)
        if len(short_term) < 5:
            return False, ""

        if len(short_term) >= 10:
            messages = [f"{m['role']}: {m['content'][:100]}" for m in short_term[-10:]]
            summary = " | ".join(messages)
            return True, summary

        return False, ""

    def add_long_term(self, user_id: str, role_id: str, content: str):
        """添加长期对话记忆"""
        key = f"{user_id}:{role_id}"
        with self._lock:
            if key not in self.long_term:
                self.long_term[key] = []

            self.long_term[key].append({
                "content": content,
                "weight": 1.0,
                "timestamp": time.time(),
                "access_count": 0,
                "decay_factor": 1.0,
            })

        logger.info(f"长期对话记忆已添加: {key}")

    def get_long_term(self, user_id: str, role_id: str, top_k: int = 5) -> list:
        """获取长期对话记忆，按权重排序"""
        key = f"{user_id}:{role_id}"
        with self._lock:
            memories = self.long_term.get(key, [])
            memories.sort(key=lambda x: x["weight"] * x["decay_factor"], reverse=True)
            return memories[:top_k]

    def apply_decay(self, user_id: str = None, role_id: str = None):
        """应用遗忘机制：按时间衰减"""
        now = time.time()
        decay_seconds = self.decay_days * 24 * 3600

        with self._lock:
            keys_to_check = []
            if user_id and role_id:
                keys_to_check = [f"{user_id}:{role_id}"]
            else:
                keys_to_check = list(self.long_term.keys())

            for key in keys_to_check:
                memories = self.long_term.get(key, [])
                for mem in memories:
                    age = now - mem["timestamp"]
                    if age > decay_seconds:
                        mem["decay_factor"] = max(0.1, 1.0 - (age / (decay_seconds * 2)))

                    if mem["access_count"] == 0 and age > decay_seconds / 2:
                        mem["decay_factor"] = max(0.1, mem["decay_factor"] * 0.8)

                self.long_term[key] = [m for m in memories if m["decay_factor"] > 0.15]

        logger.info("对话记忆遗忘机制已执行")

    def clear_session(self, session_id: str):
        """清除短期会话记忆"""
        with self._lock:
            if session_id in self.short_term:
                del self.short_term[session_id]
        logger.info(f"短期会话记忆已清除: {session_id}")

    def get_context_for_llm(self, session_id: str, user_id: str, role_id: str) -> str:
        """获取供 LLM 使用的记忆上下文"""
        parts = []

        short = self.get_short_term(session_id)
        if short:
            recent = short[-5:]
            parts.append("## 近期对话")
            for m in recent:
                parts.append(f"{m['role']}: {m['content'][:200]}")

        long = self.get_long_term(user_id, role_id, top_k=3)
        if long:
            parts.append("## 长期对话记忆")
            for m in long:
                parts.append(f"- {m['content'][:200]}")

        return "\n".join(parts) if parts else ""


conv_memory = ConversationMemory()