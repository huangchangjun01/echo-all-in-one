from datetime import datetime
from typing import Optional

from loguru import logger


class MemoryGenerator:
    """记忆生成器 Skill：生成结构化的 Markdown 记忆文档。"""

    def __init__(self, llm_client=None):
        self._llm_client = llm_client
        logger.info("MemoryGenerator initialized")

    def generate(
        self,
        parsed_contents: list[dict],
        theme_name: str,
        subjective_desc: str,
        memory_id: str,
        file_sources: list[dict],
    ) -> str:
        """
        生成结构化的 Markdown 记忆文档。

        Args:
            parsed_contents: [{"file_name": "xxx", "file_type": "text", "content": "..."}, ...]
            theme_name: 记忆主题名称
            subjective_desc: 用户主观描述
            memory_id: 唯一记忆标识
            file_sources: 源文件信息列表 [{"file_name": "xxx", "file_type": "text"}, ...]

        Returns:
            完整的 Markdown 字符串
        """
        # 1. 合并所有解析内容
        combined_text = "\n".join([
            item.get("content", "") for item in parsed_contents
        ])

        # 2. 调用 LLM 生成摘要（不超过200字）
        summary = self._generate_summary(combined_text, theme_name, subjective_desc)

        # 3. 调用 LLM 提取元数据
        metadata = self._extract_metadata(combined_text, file_sources)

        # 4. 生成记忆细节段落（每段标识来源）
        details = []
        for item in parsed_contents:
            details.append({
                "source": item.get("file_name", "未知来源"),
                "content": item.get("content", ""),
            })

        # 5. 按模板拼接 Markdown
        if self._llm_client:
            try:
                md_content = self._llm_client.generate_memory_md(
                    metadata=metadata,
                    details=details,
                    subjective_desc=subjective_desc,
                    theme_name=theme_name,
                )
                logger.info(f"Memory generated via LLM: memory_id={memory_id}, length={len(md_content)}")
                return md_content
            except Exception as e:
                logger.warning(f"LLM generate_memory_md failed, using template fallback: {e}")

        # 模板 fallback
        md_content = self._build_template(
            theme_name=theme_name,
            summary=summary,
            metadata=metadata,
            details=details,
            subjective_desc=subjective_desc,
        )
        logger.info(f"Memory generated via template: memory_id={memory_id}, length={len(md_content)}")
        return md_content

    def _generate_summary(self, combined_text: str, theme_name: str, subjective_desc: str) -> str:
        """生成摘要（不超过200字）。"""
        if self._llm_client:
            try:
                prompt = f"主题：{theme_name}\n{combined_text}"
                if subjective_desc:
                    prompt += f"\n主观描述：{subjective_desc}"
                return self._llm_client.summarize(prompt, max_length=200)
            except Exception as e:
                logger.warning(f"LLM summary failed, using fallback: {e}")

        fallback = f"关于「{theme_name}」的记忆记录。"
        if subjective_desc:
            fallback += f" {subjective_desc[:100]}"
        if combined_text:
            fallback += f" 内容：{combined_text[:100]}"
        return fallback[:200]

    def _extract_metadata(self, combined_text: str, file_sources: list[dict]) -> dict:
        """提取元数据。"""
        if self._llm_client:
            try:
                result = self._llm_client.extract_metadata(combined_text)
                if result and isinstance(result, dict):
                    return result
            except Exception as e:
                logger.warning(f"LLM metadata extraction failed, using fallback: {e}")

        now = datetime.now()
        return {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "location": "未知",
            "characters": [],
            "emotion_tags": [],
            "intensity": 5,
            "parent_skill": "无",
            "prev_skill": "无",
            "next_skill": "无",
            "sources": ", ".join([s.get("file_name", "") for s in file_sources]),
        }

    def _build_template(
        self,
        theme_name: str,
        summary: str,
        metadata: dict,
        details: list[dict],
        subjective_desc: str,
    ) -> str:
        """使用模板构建 Markdown。"""
        lines = []
        lines.append(f"# {theme_name}")
        lines.append("")

        # 摘要
        lines.append("## 摘要")
        lines.append("")
        lines.append(summary)
        lines.append("")

        # 元数据
        lines.append("## 元数据")
        lines.append("")
        lines.append(f"- 时间: {metadata.get('time', '未知')}")
        lines.append(f"- 地点: {metadata.get('location', '未知')}")
        characters = metadata.get("characters", [])
        if isinstance(characters, list):
            lines.append(f"- 人物: {', '.join(characters) if characters else '无'}")
        else:
            lines.append(f"- 人物: {characters}")
        emotion_tags = metadata.get("emotion_tags", [])
        if isinstance(emotion_tags, list):
            lines.append(f"- 情感标签: {', '.join(emotion_tags) if emotion_tags else '无'}")
        else:
            lines.append(f"- 情感标签: {emotion_tags}")
        lines.append(f"- 父Skill: {metadata.get('parent_skill', '无')}")
        lines.append(f"- 前序Skill: {metadata.get('prev_skill', '无')}")
        lines.append(f"- 后续Skill: {metadata.get('next_skill', '无')}")
        lines.append(f"- 强度: {metadata.get('intensity', 5)}")
        lines.append(f"- 来源: {metadata.get('sources', '未知')}")
        lines.append("")

        # 记忆细节
        lines.append("## 记忆细节")
        lines.append("")
        for idx, detail in enumerate(details, start=1):
            source = detail.get("source", "未知来源")
            content = detail.get("content", "")
            lines.append(f"### 片段 {idx} [来源: {source}]")
            lines.append("")
            lines.append(content)
            lines.append("")

        # 主观描述
        lines.append("## 记忆主观描述")
        lines.append("")
        lines.append(subjective_desc)
        lines.append("")

        return "\n".join(lines)