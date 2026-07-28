from fastapi import APIRouter
from loguru import logger

from app.models.schemas import APIResponse
from app.services.conversation_memory import conv_memory

router = APIRouter(prefix="/api/ai/chat", tags=["chat"])


def _get_services():
    """Lazy import to avoid circular dependency."""
    from app.main import get_services
    return get_services()


@router.post("/memory-search", response_model=APIResponse)
async def chat_memory_search(request: dict):
    """
    对话记忆检索：根据消息内容检索 Top5 相关记忆，并返回对话记忆上下文。
    """
    user_id = request.get("user_id")
    role_id = request.get("role_id")
    message = request.get("message", "")
    session_id = request.get("session_id", "default")

    services = _get_services()
    vector_store = services["vector_store"]

    # 1. 检索回忆记忆（向量库 Top5）
    memories = vector_store.search(message, top_k=5, user_id=user_id, role_id=role_id)

    # 2. 获取对话记忆上下文
    dialogue_context = conv_memory.get_context_for_llm(session_id, user_id, role_id)

    # 3. 存储当前消息到对话记忆
    conv_memory.add_message(session_id, user_id, role_id, "user", message)

    logger.info(
        f"Chat memory search: user={user_id}, role={role_id}, "
        f"found={len(memories)} memories"
    )
    return APIResponse(
        code=0,
        message="success",
        data={
            "recall_memories": memories,
            "dialogue_context": dialogue_context,
        },
    )


@router.post("/memory-detail", response_model=APIResponse)
async def chat_memory_detail(request: dict):
    """
    追问记忆细节：获取完整记忆内容，同时检索其他相关记忆摘要。
    """
    user_id = request.get("user_id")
    role_id = request.get("role_id")
    memory_id = request.get("memory_id")
    message = request.get("message", "")

    services = _get_services()
    storage = services["storage"]
    vector_store = services["vector_store"]

    # 1. 获取目标记忆的完整 md 文件
    md_key = f"memory/{user_id}/{role_id}/{memory_id}/{memory_id}.md"
    try:
        md_content = storage.download_content(md_key)
    except FileNotFoundError:
        logger.warning(f"Memory detail not found: md_key={md_key}")
        return APIResponse(code=404, message="记忆文件不存在", data=None)

    # 2. 同时检索其他相关记忆的摘要
    other_memories = vector_store.search(message, top_k=3, user_id=user_id, role_id=role_id)
    other_memories = [m for m in other_memories if m.get("memory_id") != memory_id]

    logger.info(
        f"Chat memory detail: memory_id={memory_id}, "
        f"related={len(other_memories)}"
    )
    return APIResponse(
        code=0,
        message="success",
        data={
            "memory_detail": md_content,
            "related_memories": other_memories,
        },
    )


@router.post("/conversation-memory", response_model=APIResponse)
async def conversation_memory_manage(request: dict):
    """
    对话记忆管理：存储消息、转化长期记忆、执行遗忘检查。
    """
    user_id = request.get("user_id")
    role_id = request.get("role_id")
    session_id = request.get("session_id", "default")
    messages = request.get("messages", [])

    # 1. 存储消息到短期记忆
    for msg in messages:
        conv_memory.add_message(
            session_id, user_id, role_id,
            msg.get("role", "user"), msg.get("content", ""),
        )

    # 2. 检查是否需要转化长期记忆
    should_convert, summary = conv_memory.should_convert_to_long_term(session_id)
    if should_convert:
        conv_memory.add_long_term(user_id, role_id, summary)

    # 3. 执行遗忘检查
    conv_memory.apply_decay(user_id, role_id)

    long_term_count = len(conv_memory.get_long_term(user_id, role_id))
    logger.info(
        f"Conversation memory managed: user={user_id}, role={role_id}, "
        f"converted={should_convert}, long_term={long_term_count}"
    )
    return APIResponse(
        code=0,
        message="success",
        data={
            "converted": should_convert,
            "long_term_count": long_term_count,
        },
    )