import re
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.models.schemas import (
    APIResponse,
    MemoryParseRequest,
    MemoryFileDeleteRequest,
    MemoryThemeDeleteRequest,
)

router = APIRouter(prefix="/api/ai", tags=["memory"])


def _get_services():
    """Lazy import to avoid circular dependency."""
    from app.main import get_services
    return get_services()


@router.post("/memory/parse", response_model=APIResponse)
async def parse_memory(request: MemoryParseRequest):
    """解析记忆文件并生成结构化记忆文档。"""
    services = _get_services()
    lock_mgr = services["lock_manager"]
    memory_id = request.memory_id

    # 1. 获取编辑状态锁
    if not lock_mgr.acquire(memory_id):
        logger.error(f"Failed to acquire lock for memory_id={memory_id}")
        return APIResponse(code=409, message="记忆正在编辑中，请稍后重试", data=None)

    try:
        storage_svc = services["storage"]
        parser_svc = services["parser"]
        memory_gen = services["memory_generator"]
        vector_svc = services["vector_store"]

        temp_dir = Path(tempfile.gettempdir()) / f"memory_parse_{memory_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 2. 从 storage 下载所有源文件到临时目录
            parsed_contents = []
            for file_info in request.files:
                local_path = str(temp_dir / file_info.file_name)
                try:
                    storage_svc.download_file(file_info.file_key, local_path)
                    # 3. 对每个文件调用 parser.parse_file() 解析
                    content = parser_svc.parse_file(local_path, file_info.file_type)
                    parsed_contents.append({
                        "file_name": file_info.file_name,
                        "file_type": file_info.file_type,
                        "content": content,
                    })
                    logger.info(f"Parsed file: {file_info.file_name}, type={file_info.file_type}")
                except Exception as e:
                    logger.error(f"Failed to parse file {file_info.file_name}: {e}")
                    parsed_contents.append({
                        "file_name": file_info.file_name,
                        "file_type": file_info.file_type,
                        "content": f"[解析失败: {file_info.file_name}] {str(e)}",
                    })

            file_sources = [
                {"file_name": f.file_name, "file_type": f.file_type}
                for f in request.files
            ]

            # 4. 调用 memory_generator.generate() 生成 Markdown
            md_content = memory_gen.generate(
                parsed_contents=parsed_contents,
                theme_name=request.theme_name,
                subjective_desc=request.subjective_desc,
                memory_id=memory_id,
                file_sources=file_sources,
            )

            # 5. 将 {memory_id}.md 上传到对象存储
            # 路径格式: memory/{user_id}/{role_id}/{memory_id}/{memory_id}.md
            md_key = f"memory/{request.user_id}/{request.role_id}/{memory_id}/{memory_id}.md"
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(md_content)
                tmp_path = tmp.name
            try:
                storage_svc.upload_file(tmp_path, md_key)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

            # 6. 使用摘要生成向量，存入向量库
            # 提取摘要文本作为向量内容
            summary_match = re.search(r"## 摘要\n\n(.+?)\n\n", md_content, re.DOTALL)
            summary_text = summary_match.group(1).strip() if summary_match else md_content[:500]
            vector_svc.add_vector(
                text=summary_text,
                user_id=request.user_id,
                role_id=request.role_id,
                memory_id=memory_id,
                md_key=md_key,
            )

            logger.info(
                f"Memory parsed: memory_id={memory_id}, theme={request.theme_name}, "
                f"files={len(request.files)}"
            )
            return APIResponse(code=0, message="success", data={"md_key": md_key})

        finally:
            # 7. 清理临时文件
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        logger.exception(f"Memory parse failed: {e}")
        return APIResponse(code=500, message=str(e), data=None)

    finally:
        # 8. 释放编辑状态锁
        lock_mgr.release(memory_id)


@router.post("/memory/file-delete", response_model=APIResponse)
async def delete_memory_file(request: MemoryFileDeleteRequest):
    """删除记忆中的某个源文件，更新对应 md 文档和向量库。"""
    services = _get_services()
    lock_mgr = services["lock_manager"]
    memory_id = request.memory_id

    # 1. 获取编辑状态锁
    if not lock_mgr.acquire(memory_id):
        logger.error(f"Failed to acquire lock for memory_id={memory_id}")
        return APIResponse(code=409, message="记忆正在编辑中，请稍后重试", data=None)

    try:
        storage_svc = services["storage"]
        vector_svc = services["vector_store"]

        md_key = f"memory/{request.user_id}/{request.role_id}/{memory_id}/{memory_id}.md"

        # 2. 从 storage 下载当前 {memory_id}.md
        temp_dir = Path(tempfile.gettempdir()) / f"memory_filedel_{memory_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        local_md = str(temp_dir / f"{memory_id}.md")

        try:
            storage_svc.download_file(md_key, local_md)
            md_content = Path(local_md).read_text(encoding="utf-8")
        except Exception:
            logger.warning(f"MD file not found: {md_key}, skipping md update")
            md_content = None

        if md_content:
            # 3. 解析 md 文件，找到对应源文件的记忆细节段落并删除
            new_md_content = _remove_file_section(md_content, request.file_name)

            # 4. 重新生成摘要（提取更新后的摘要文本）
            summary_match = re.search(r"## 摘要\n\n(.+?)\n\n", new_md_content, re.DOTALL)
            summary_text = summary_match.group(1).strip() if summary_match else new_md_content[:500]

            # 5. 更新 md 文件内容
            with open(local_md, "w", encoding="utf-8") as f:
                f.write(new_md_content)

            # 6. 上传覆盖原有 md 文件
            storage_svc.upload_file(local_md, md_key)

            # 7. 更新向量库中的摘要
            vector_svc.update_vector(memory_id=memory_id, new_text=summary_text)
        else:
            # 如果 md 不存在，直接删除向量
            vector_svc.delete_vectors(memory_id=memory_id)

        # 同时删除源文件
        storage_svc.delete_directory(request.file_key)

        logger.info(
            f"Memory file deleted: memory_id={memory_id}, file_name={request.file_name}"
        )
        return APIResponse(code=0, message="success", data=None)

    except Exception as e:
        logger.exception(f"Memory file delete failed: {e}")
        return APIResponse(code=500, message=str(e), data=None)

    finally:
        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        # 8. 释放锁
        lock_mgr.release(memory_id)


def _remove_file_section(md_content: str, file_name: str) -> str:
    """从 Markdown 内容中移除指定来源文件的记忆细节片段。"""
    # 匹配 ### 片段 N [来源: file_name] 及其后续内容
    pattern = rf"### 片段 \d+ \[来源: {re.escape(file_name)}\].*?(?=### 片段 \d+ \[来源:|## 记忆主观描述|$)"
    new_content = re.sub(pattern, "", md_content, flags=re.DOTALL)

    # 清理多余的空行
    new_content = re.sub(r"\n{3,}", "\n\n", new_content)
    return new_content.strip() + "\n"


@router.post("/memory/theme-delete", response_model=APIResponse)
async def delete_memory_theme(request: MemoryThemeDeleteRequest):
    """删除整个记忆主题及所有关联文件和向量。"""
    services = _get_services()
    storage_svc = services["storage"]
    vector_svc = services["vector_store"]

    memory_id = request.memory_id
    user_id = request.user_id
    role_id = request.role_id

    try:
        # 1. 删除对象存储中 /memory/{user_id}/{role_id}/{memory_id}/ 目录下所有文件
        storage_prefix = f"memory/{user_id}/{role_id}/{memory_id}"
        storage_svc.delete_directory(storage_prefix)
        logger.info(f"Deleted storage directory: {storage_prefix}")

        # 2. 删除向量库中所有关联记录
        deleted_count = vector_svc.delete_vectors(memory_id=memory_id)
        logger.info(
            f"Memory theme deleted: memory_id={memory_id}, "
            f"user_id={user_id}, role_id={role_id}, vectors_deleted={deleted_count}"
        )

        return APIResponse(code=0, message="success", data={"deleted_vectors": deleted_count})

    except Exception as e:
        logger.exception(f"Memory theme delete failed: {e}")
        return APIResponse(code=500, message=str(e), data=None)


@router.get("/health")
async def health_check():
    """健康检查接口。"""
    return {"status": "ok"}