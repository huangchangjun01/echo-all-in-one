import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import faiss
from loguru import logger

from app.config import config


class VectorStoreService:
    """基于 FAISS + numpy 的向量存储服务，支持语义搜索。"""

    def __init__(self):
        vs_cfg = config.vector_store
        self._dimension = vs_cfg.get("dimension", 1536)
        self._index_path = Path(vs_cfg.get("index_path", "./data/vector_store"))
        self._index_path.mkdir(parents=True, exist_ok=True)

        self._index = None
        self._metadata: dict[int, dict] = {}
        self._next_id: int = 0

        self._load()

        logger.info(
            f"VectorStoreService initialized, dimension={self._dimension}, "
            f"vectors={self._index.ntotal if self._index else 0}"
        )

    def _generate_vector(self, text: str = "") -> np.ndarray:
        """生成随机归一化向量（模拟 embedding）。"""
        vec = np.random.randn(self._dimension).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        return vec

    def _save(self):
        """持久化 FAISS 索引和元数据到磁盘。"""
        index_file = self._index_path / "faiss.index"
        meta_file = self._index_path / "metadata.pkl"

        faiss.write_index(self._index, str(index_file))
        with open(meta_file, "wb") as f:
            pickle.dump({"metadata": self._metadata, "next_id": self._next_id}, f)

        logger.debug(f"Vector store saved: {self._index.ntotal} vectors")

    def _load(self):
        """从磁盘加载 FAISS 索引和元数据。"""
        index_file = self._index_path / "faiss.index"
        meta_file = self._index_path / "metadata.pkl"

        if index_file.exists() and meta_file.exists():
            self._index = faiss.read_index(str(index_file))
            with open(meta_file, "rb") as f:
                data = pickle.load(f)
            self._metadata = data.get("metadata", {})
            self._next_id = data.get("next_id", 0)
            logger.info(f"Vector store loaded: {self._index.ntotal} vectors, next_id={self._next_id}")
        else:
            self._index = faiss.IndexFlatIP(self._dimension)
            self._metadata = {}
            self._next_id = 0
            logger.info("Created new FAISS index")

    def add_vector(self, text: str, user_id: str, role_id: str, memory_id: str, md_key: str) -> int:
        """添加向量及其元数据到存储中。"""
        vector = self._generate_vector(text).reshape(1, -1)
        vec_id = self._next_id
        self._next_id += 1

        self._index.add(vector)
        self._metadata[vec_id] = {
            "text": text,
            "user_id": user_id,
            "role_id": role_id,
            "memory_id": memory_id,
            "md_key": md_key,
        }

        logger.debug(f"Vector added: id={vec_id}, memory_id={memory_id}, md_key={md_key}")
        self._save()
        return vec_id

    def search(
        self,
        query_text: str = "",
        top_k: int = 5,
        user_id: Optional[str] = None,
        role_id: Optional[str] = None,
    ) -> list[dict]:
        """根据查询文本搜索相似向量，支持 user_id/role_id 过滤。"""
        if self._index.ntotal == 0:
            return []

        query_vector = self._generate_vector(query_text).reshape(1, -1)

        actual_k = min(top_k, self._index.ntotal)
        distances, indices = self._index.search(query_vector, actual_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx not in self._metadata:
                continue
            meta = self._metadata[idx]
            if user_id and meta.get("user_id") != user_id:
                continue
            if role_id and meta.get("role_id") != role_id:
                continue
            results.append({
                "id": int(idx),
                "score": float(dist),
                **meta,
            })

        return results

    def update_vector(self, memory_id: str, new_text: str) -> int:
        """更新指定 memory_id 的向量：先删除旧向量再添加新向量。"""
        self.delete_vectors(memory_id=memory_id)
        new_id = self.add_vector(
            text=new_text,
            user_id="",
            role_id="",
            memory_id=memory_id,
            md_key="",
        )
        logger.info(f"Vector updated: memory_id={memory_id}, new_id={new_id}")
        return new_id

    def delete_vectors(
        self,
        memory_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role_id: Optional[str] = None,
    ) -> int:
        """删除匹配过滤条件的向量，返回删除数量。"""
        to_delete = []
        for vec_id, meta in self._metadata.items():
            if memory_id and meta.get("memory_id") == memory_id:
                to_delete.append(vec_id)
            elif user_id and meta.get("user_id") == user_id:
                to_delete.append(vec_id)
            elif role_id and meta.get("role_id") == role_id:
                to_delete.append(vec_id)

        if not to_delete:
            return 0

        for vec_id in to_delete:
            del self._metadata[vec_id]

        remaining = sorted(set(self._metadata.keys()) - set(to_delete))
        if not remaining:
            self._index = faiss.IndexFlatIP(self._dimension)
            logger.info("All vectors deleted, index reset")
        else:
            new_index = faiss.IndexFlatIP(self._dimension)
            vectors = []
            new_metadata = {}
            new_id = 0
            for old_id in remaining:
                vec = self._index.reconstruct(old_id)
                vectors.append(vec)
                new_metadata[new_id] = self._metadata[old_id]
                new_id += 1
            if vectors:
                new_index.add(np.array(vectors, dtype=np.float32))
            self._index = new_index
            self._metadata = new_metadata
            self._next_id = new_id

        self._save()
        logger.info(f"Deleted {len(to_delete)} vectors")
        return len(to_delete)