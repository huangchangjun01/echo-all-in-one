import json
from typing import Optional

from openai import OpenAI
from loguru import logger

from app.config import config


class LLMClient:
    """LLM client based on OpenAI SDK, with mock mode fallback when API key is unavailable."""

    def __init__(self):
        llm_cfg = config.llm
        api_key = llm_cfg.get("api_key", "")
        base_url = llm_cfg.get("base_url", "https://api.openai.com/v1")
        self._model = llm_cfg.get("model", "gpt-4o-mini")

        self._mock_mode = not api_key
        if self._mock_mode:
            logger.warning("OPENAI_API_KEY not set, LLM will run in mock mode")
        else:
            self._client = OpenAI(api_key=api_key, base_url=base_url)

        logger.info(
            f"LLMClient initialized, model={self._model}, base_url={base_url}, "
            f"mock_mode={self._mock_mode}"
        )

    def chat_completion(self, messages: list[dict], temperature: float = 0.7) -> str:
        """通用对话补全"""
        if self._mock_mode:
            logger.debug("LLM mock mode: returning placeholder for chat_completion")
            user_content = ""
            for msg in messages:
                if msg.get("role") == "user":
                    user_content = msg.get("content", "")
                    break
            return f"[Mock] 基于输入的回复（{len(user_content)} 字符）"

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
            )
            content = response.choices[0].message.content or ""
            logger.debug(f"LLM chat_completion: {len(content)} chars returned")
            return content
        except Exception as e:
            logger.error(f"LLM chat_completion failed: {e}")
            raise

    def summarize(self, text: str, max_length: int = 200) -> str:
        """使用 LLM 将文本整理为语义通顺的摘要，不超过 max_length 字"""
        if self._mock_mode:
            logger.debug("LLM mock mode: generating placeholder summary")
            cleaned = text.replace("\n", " ").strip()
            return cleaned[:max_length] if cleaned else f"[Mock 摘要] 内容共 {len(text)} 字符"

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的文本摘要助手。将以下内容整理为语义通顺的摘要，不改变内容和细节。",
            },
            {"role": "user", "content": f"请用不超过{max_length}字概括以下内容：\n\n{text}"},
        ]
        try:
            result = self.chat_completion(messages, temperature=0.3)
            return result
        except Exception as e:
            logger.error(f"LLM summarize failed: {e}")
            return text[:max_length]

    def extract_metadata(self, text: str) -> dict:
        """从文本中提取元数据：时间、地点、人物、情感标签、强度"""
        if self._mock_mode:
            logger.debug("LLM mock mode: generating placeholder metadata")
            return {
                "time": "未知",
                "location": "未知",
                "characters": [],
                "emotion_tags": [],
                "intensity": 5,
            }

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的元数据提取助手。请从文本中提取以下信息，"
                    "以JSON格式返回，字段包括：time(时间)、location(地点)、"
                    "characters(人物列表)、emotion_tags(情感标签列表)、"
                    "intensity(情感强度1-10)。只返回JSON，不要其他内容。"
                ),
            },
            {"role": "user", "content": f"请提取以下文本的元数据：\n\n{text}"},
        ]
        try:
            result = self.chat_completion(messages, temperature=0.3)
            # 尝试解析 JSON
            result = result.strip()
            if result.startswith("```"):
                lines = result.split("\n")
                result = "\n".join(lines[1:-1])
            return json.loads(result)
        except Exception as e:
            logger.error(f"LLM extract_metadata failed: {e}")
            return {
                "time": "未知",
                "location": "未知",
                "characters": [],
                "emotion_tags": [],
                "intensity": 5,
            }

    def generate_memory_md(
        self,
        metadata: dict,
        details: list,
        subjective_desc: str,
        theme_name: str,
    ) -> str:
        """生成结构化的 Markdown 记忆文件（使用模板拼接，不调用 LLM）"""
        lines = []
        lines.append(f"# {theme_name}")
        lines.append("")

        # 摘要
        summary = metadata.get("summary", "")
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
            lines.append(f"- 人物: {', '.join(characters) if characters else '未知'}")
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
            source = detail.get("source", f"未知来源")
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