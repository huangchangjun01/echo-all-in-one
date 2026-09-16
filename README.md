# Echo All-in-One

Echo 虚拟陪伴平台 —— 单体仓库（Monorepo），聚合三个独立服务：

| 子项目 | 目录 | 技术栈 | 职责 |
| --- | --- | --- | --- |
| **echo-web** | `web/` | Vue 3 + TypeScript + Vite 8 + Element Plus | 前端：SSE 流式对话、语音交互、七牛直传、以「记忆主题」为单位的记忆管理 |
| **echo-core** | `core/` | Go + Gin + GORM + MySQL + 七牛 SDK | 后端 API：鉴权、角色、文件/记忆元数据、对话透传、健康探针 |
| **echo-ai** | `ai/` | Python + FastAPI + Weaviate + LLM | AI 引擎：意图识别、ReAct + 级联对话、多模态 Embedding / RAG、回忆记忆解析 |

## 架构

```
┌──────────┐   SSE / JSON    ┌──────────┐   HTTP 透传   ┌──────────┐
│  echo-web │ ──────────────► │ echo-core │ ───────────► │ echo-ai  │
│  :5173    │   /api 代理      │ :8080     │ :8000       │ :8000    │
└──────────┘                 └────┬─────┘              └────┬─────┘
                                  │ GORM                    │ aiomysql / SDK
                              ┌───▼────┐              ┌─────▼──────┐
                              │ MySQL   │              │ Weaviate   │
                              │ Qiniu   │              │ 七牛 OSS   │
                              └─────────┘              │ LLM API    │
                                                        └────────────┘
```

- 浏览器访问前端 `:5173`，`/api` 由 Vite 代理到 `echo-core :8080`。
- `echo-core` 负责鉴权与业务落库，AI 能力（对话、RAG、记忆解析）全部透传给 `echo-ai`。
- `echo-ai` 通过内部 Token 回调 `echo-core`（`/api/memory/*` 内部接口）同步解析状态与 md 缓存。

## 端口一览

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| echo-web (dev) | http://localhost:5173 | Vite dev server，`/api` 代理到 8080 |
| echo-core | http://localhost:8080 | `GET /health`、`/api/auth|role|file|memory|chat` |
| echo-ai | http://localhost:8000 | `GET /health`、`/chat`、`/ingest_file`、`/memory/*` |
| MySQL | 见各 `.env`（默认远程 8.130.81.41:3306） | 两服务共用同一库 `huangchangjun` |
| Weaviate | 见 `ai/.env`（`WEAVIATE_HOST=8.130.81.41:8080`，远程，与 core 无本地端口冲突） | 向量库 |

## 子模块（Submodule）

`web/`、`core/`、`ai/` 均为 **git submodule**，各自指向独立的源仓库（本地路径，默认分支 `master`，见 `.gitmodules`）：

| 子模块 | 路径 | 源仓库 |
| --- | --- | --- |
| echo-web | `web/` | `E:/FE/workspace/echo-web` |
| echo-core | `core/` | `E:/Goland/Workspace/echo-core` |
| echo-ai | `ai/` | `E:/python/workspace/echo-ai` |

**同步机制**：在源仓库编辑并提交 → 回到本仓库执行 `git submodule update --remote web`（可只更新单个）→ 聚合仓库记录新的 commit 指针 → 再提交聚合仓库。

```bash
# 更新全部子模块到源仓库最新 master（并让聚合仓库记录新指针）
git submodule update --remote

# 仅更新某个子模块
git submodule update --remote core

# 首次 clone 本仓库后，初始化并拉取子模块内容
git submodule update --init --recursive
```

> 子模块工作树是各自独立的 git 仓库：在 `web/`、`core/`、`ai/` 内部也可以直接 `git pull` / 编辑提交，效果等同操作源仓库。

## 目录结构

```
echo-all-in-one/
├── web/                      # submodule → echo-web（Vue 前端，完整 README 见 web/README.md）
├── core/                     # submodule → echo-core（Go 后端，完整 README 见 core/README.md + ARCHITECTURE.md）
├── ai/                       # submodule → echo-ai（Python AI 服务，完整 README 见 ai/README.md）
├── .gitmodules               # 三个子模块的路径 / URL / 分支映射
├── scripts/
│   ├── start-all.ps1         # 一键启动 ai → core → web（自动编译、健康检查、日志落 logs/）
│   └── stop-all.ps1          # 按 PID 记录停掉全部服务（含子进程树）
├── .gitignore                # 根级忽略：.env / 日志 / 构建产物（不覆盖子项目自身规则）
└── README.md
```

## 本地配置（.env 矩阵）

每个服务在**自身目录**读取 `.env`（core / ai 用 CWD 定位）。合并后关键配置：

| 变量 | web/.env | core/.env | ai/.env |
| --- | --- | --- | --- |
| 监听端口 | `VITE_API_BASE_URL`(默认 `/api`) | `APP_PORT=8080` | `APP_PORT=8000` |
| MySQL | - | `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` | 同 core 的 `DB_*` |
| 七牛云 | `.env.qiniu`（前端上传备用） | `QINIU_ACCESS_KEY/SECRET_KEY/BUCKET_NAME/DOMAIN` | `QINIU_ACCESS_KEY/SECRET_KEY/BUCKET_NAME` |
| LLM | `VITE_DEFAULT_CHAT_MODEL` | `LLM_*`（预留） | `LLM_*` / `LLM_SMALL_*`（实际生效） |
| 互相调用 | - | `ECHO_AI_REMOTE_BASE_URL=http://localhost:8000` | `WEAVIATE_HOST` / `EMBEDDING_*` / `BGE_M3_*` |

> **安全提醒**：三个 `.env` 均含真实密钥，根 `.gitignore` 已将其排除，**严禁提交**。

## 快速开始

### 方式一：一键脚本（Windows）

```powershell
# 前置：已安装 Go ≥1.25、Node.js ≥20、Python 3.10+；MySQL / 远程依赖可达
.\scripts\start-all.ps1        # 启动全部
.\scripts\start-all.ps1 -Only core   # 只启动某个服务
.\scripts\stop-all.ps1         # 停止全部
```

日志输出到 `logs/`（ai.out.log / core.out.log / web.out.log 等）。

### 方式二：手动逐个启动

```bash
# 1. ai（推荐先建虚拟环境）
cd ai && python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py                  # :8000

# 2. core
cd core && go mod tidy && go build -o .bin\echo-core.exe . && .\.bin\echo-core.exe   # :8080

# 3. web
cd web && npm install && npm run dev    # :5173
```

## 测试

```bash
cd web && npm test          # node:test + vitest（SSE 协议 / 附件渲染 / 打字机 / 七牛上传队列）
cd core && go test ./service -run 'TestResolveSourceFileType|TestInferFileTypeByExt'
cd ai   && pytest           # 需先安装依赖与配置 .env
```

## 注意事项

- **端口冲突**：`web/server.go` 是历史遗留的 Go Mock 后端（占用 8080），与 `echo-core` **冲突**，同一时间只能运行一个；仅做前端本地联调时可单跑它。
- **ai 启动慢**：首次启动需下载/加载本地模型（Chinese-CLIP / Whisper / BGE-M3），模型文件较大，`/health` 可能延迟数分钟才返回 200。
- **镜像源**：国内环境确保 `ai/.env` 设置 `EMBEDDING_ENDPOINT` / `BGE_M3_ENDPOINT=https://hf-mirror.com`，否则模型下载会直连 huggingface.co 失败。
- **源仓库为准**：`web/` `core/` `ai/` 工作树与各自源仓库（echo-web / echo-core / echo-ai）是同一份代码（submodule 从本地源仓库 clone）。在聚合仓库内编辑后 commit 的是**子仓库自己的历史**；聚合仓库仅在 `git submodule update --remote` 后记录新的 commit 指针。

## 其他

- 演进需求与原型（产品层）：见 `.trae/specs/echo-evolution-detail/`（历史产物，与本仓库代码无耦合）。