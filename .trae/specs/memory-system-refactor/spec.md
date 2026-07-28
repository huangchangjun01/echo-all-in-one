# 记忆系统重构 Spec

## Why
虚拟陪伴平台需要持久化、结构化的记忆系统，以支撑长期陪伴场景。现有记忆系统存在存储方式单一、无法处理多模态记忆、缺少向量检索与渐进式回忆能力等问题。本次重构采用"文档即记忆"思想，将记忆以 Markdown 文档形式存储于对象存储，结合 AI 解析与向量检索，实现"渐进式回忆"能力。

## What Changes
- 前端：重构记忆管理页面，支持多模态文件上传（文本/音频/视频/图片）、分片上传、断点续传、并行上传、进度展示、在线编辑 Markdown 记忆文件
- 后端（Go）：提供记忆 CRUD 接口、文件管理、事务处理、异步 AI 调用
- AI 服务（Python）：多模态文件解析、LLM 摘要生成、记忆 Markdown 文件生成、向量库管理、对话记忆（含遗忘机制）、回忆记忆（永不遗忘）
- 新增 memory.md 生成 Skill，用于将记忆源文件解析为结构化 Markdown 记忆文档
- 对话模块集成向量检索，根据对话内容检索 Top5 相关记忆辅助生成回复

## Impact
- Affected specs: 无（全新项目）
- Affected code: 前端 Vue 项目、后端 Go 服务、AI Python 服务（均为新建）

---

## ADDED Requirements

### Requirement: 记忆主题管理（前端）
系统 SHALL 提供记忆管理页面，支持记忆主题的创建、查看、编辑和删除。

#### Scenario: 创建记忆主题
- **WHEN** 用户在记忆管理页面点击"新增"按钮
- **THEN** 弹出新增弹窗，包含：记忆主题（必填、唯一）、记忆源文件（必填、支持多文件上传）、记忆主观描述（非必填、限1000字）
- **AND** 记忆主题输入框提示用户填写"时间+地点+人物+事件"格式
- **AND** 记忆主题名称一经创建，永不可编辑

#### Scenario: 记忆主题唯一性校验
- **WHEN** 用户填写记忆主题名称并失焦
- **THEN** 调用后端接口校验该主题在当前用户、当前角色下是否唯一
- **AND** 若不唯一，阻止提交并提示用户

#### Scenario: 查看记忆主题
- **WHEN** 用户点击列表中的"查看"按钮
- **THEN** 弹出查看弹窗，展示记忆主题信息、记忆源文件列表和记忆内容文件
- **AND** 可点击下载记忆源文件或 {memoryId}.md 文件
- **AND** 弹窗仅有"取消"按钮，无"保存"按钮，不可编辑任何内容

#### Scenario: 编辑记忆主题
- **WHEN** 用户点击列表中的"编辑"按钮
- **THEN** 弹出编辑弹窗，可增删记忆源文件，可编辑主观描述
- **AND** 记忆内容区域显示 {memoryId}.md 文件，支持在线编辑
- **AND** 编辑 {memoryId}.md 时需二次确认
- **AND** 若 AI 正在编辑该记忆文件，则阻止手动编辑并提示用户
- **AND** 点击保存后，若有源文件增删或主观描述修改，则触发重新解析

#### Scenario: 删除记忆主题
- **WHEN** 用户点击列表中的"删除"按钮
- **THEN** 弹出二次确认弹窗
- **AND** 确认后删除对象存储文件、后端记录和向量库记录

### Requirement: 多模态文件上传（前端）
系统 SHALL 支持多模态文件上传，包括文本、音频、视频和图片，具备分片上传、断点续传、并行上传和进度展示能力。

#### Scenario: 选择多模态文件
- **WHEN** 用户点击上传区域
- **THEN** 允许选择文本（.txt/.md/.pdf/.doc/.docx）、音频（.mp3/.wav/.m4a/.aac）、视频（.mp4/.mov/.avi/.mkv）、图片（.jpg/.jpeg/.png/.gif/.webp）文件
- **AND** 支持同时选择多个文件

#### Scenario: 大文件上传确认
- **WHEN** 用户选择单个文件超过 500MB
- **THEN** 弹出确认提示，告知用户文件较大，建议确认后上传

#### Scenario: 分片上传
- **WHEN** 文件大小超过分片阈值（如 5MB）
- **THEN** 自动使用分片上传，将文件切割为多个分片依次上传
- **AND** 显示每个分片的上传进度

#### Scenario: 断点续传
- **WHEN** 分片上传过程中网络中断
- **THEN** 已上传的分片被保留
- **AND** 恢复网络后，从断点继续上传未完成的分片

#### Scenario: 并行上传
- **WHEN** 同时上传多个文件
- **THEN** 最多同时上传 5 个文件（或分片）
- **AND** 超出数量的文件进入等待队列

#### Scenario: 上传进度展示
- **WHEN** 文件正在上传
- **THEN** 每个文件显示独立的进度条，包括百分比和已上传/总大小

#### Scenario: 上传失败重试
- **WHEN** 某个文件上传失败
- **THEN** 该文件显示"重试"按钮
- **AND** 点击重试后，重新上传该文件（支持断点续传）

#### Scenario: 上传强校验
- **WHEN** 用户点击"确定"提交记忆
- **THEN** 若仍有文件上传中或上传失败，阻止提交并提示用户
- **AND** 仅当所有文件上传成功后，才调用后端保存接口

### Requirement: 记忆内容编辑（前端）
系统 SHALL 支持对 {memoryId}.md 文件的在线编辑，并在提交后重新上传至对象存储。

#### Scenario: 在线编辑记忆内容
- **WHEN** 用户在编辑弹窗中修改记忆内容
- **THEN** 提供 Markdown 编辑器
- **AND** 点击保存时，弹出二次确认弹窗
- **AND** 确认后，将编辑后的内容上传至对象存储原路径，替换旧文件

#### Scenario: AI 编辑状态冲突
- **WHEN** 用户尝试编辑记忆内容但 AI 正在写入
- **THEN** 编辑器置为只读状态，并提示"AI 正在处理该记忆，请稍后再试"
- **AND** 不允许保存

### Requirement: 记忆保存接口（后端 Go）
系统 SHALL 提供记忆保存 REST API，接收记忆主题信息并持久化，异步触发 AI 解析。

#### Scenario: 成功保存记忆
- **WHEN** 前端调用 POST /api/memory/save，传入 userId、roleId、记忆主题名称、主观描述、记忆源文件数组
- **THEN** 在事务中写入数据库（记忆主题表 + 文件表）
- **AND** 返回 memoryId
- **AND** 异步调用 AI 服务解析接口，不等待返回结果

#### Scenario: 事务回滚
- **WHEN** 数据库写入过程中发生异常
- **THEN** 事务回滚，所有数据恢复原状
- **AND** 返回错误信息

### Requirement: 记忆文件删除接口（后端 Go）
系统 SHALL 提供单个记忆源文件删除 REST API，删除文件记录后异步更新 AI 服务。

#### Scenario: 删除单个记忆源文件
- **WHEN** 前端调用 DELETE /api/memory/file，传入 memoryId、fileId
- **THEN** 在事务中删除数据库文件记录
- **AND** 异步调用 AI 服务删除文件接口，触发重新解析和向量更新
- **AND** 返回成功

### Requirement: 记忆主题删除接口（后端 Go）
系统 SHALL 提供整个记忆主题删除 REST API，删除所有关联数据。

#### Scenario: 删除整个记忆主题
- **WHEN** 前端调用 DELETE /api/memory/theme，传入 memoryId
- **THEN** 在事务中删除数据库记忆主题记录和所有关联文件记录
- **AND** 异步调用 AI 服务删除记忆接口，删除对象存储文件、更新向量库
- **AND** 返回成功

### Requirement: 申请记忆 ID 接口（后端 Go）
系统 SHALL 提供申请记忆 ID 接口，返回去除连字符的 UUID。

#### Scenario: 申请 memoryId
- **WHEN** 前端调用 POST /api/memory/apply-id
- **THEN** 生成 UUID 并去除连字符 "-"
- **AND** 返回 memoryId

### Requirement: 记忆主题唯一性校验接口（后端 Go）
系统 SHALL 提供校验记忆主题名称是否唯一的接口。

#### Scenario: 校验主题名称唯一
- **WHEN** 前端调用 GET /api/memory/check-theme，传入 userId、roleId、themeName
- **THEN** 查询数据库判断是否存在同名主题
- **AND** 返回 { exists: true/false }

### Requirement: AI 记忆文件解析（AI 服务 Python）
系统 SHALL 提供记忆文件解析接口，下载源文件、解析内容、生成摘要和记忆 Markdown 文件。

#### Scenario: 解析多模态源文件
- **WHEN** AI 服务收到解析请求（userId、roleId、memoryId、主题名称、主观描述、源文件数组）
- **THEN** 从对象存储下载所有源文件到本地临时目录
- **AND** 对文本文件直接读取内容
- **AND** 对图片调用视觉模型提取描述
- **AND** 对音频调用语音识别转文字
- **AND** 对视频提取关键帧 + 音频转文字
- **AND** 将所有解析结果汇总

#### Scenario: 生成摘要
- **WHEN** 解析完成后
- **THEN** 使用 LLM 将解析细节整理为语义通顺的文本（不改变内容和细节）
- **AND** 结合主观描述，生成不超过 200 字的摘要

#### Scenario: 生成 memory.md 文件
- **WHEN** 摘要生成完成
- **THEN** 生成 {memoryId}.md 文件，包含以下结构：
  - 摘要
  - 元数据（时间、地点、人物、情感标签、父Skill、前序Skill、后续Skill、强度、来源）
  - 记忆细节（分段，每段标识来源文件）
  - 记忆主观描述
- **AND** 上传至对象存储路径 /memory/{userId}/{roleId}/{memoryId}/

#### Scenario: 生成向量记录
- **WHEN** memory.md 上传完成
- **THEN** 使用摘要生成向量嵌入
- **AND** 存入向量库，记录包含：摘要文本、userId、roleId、memoryId、md文件key

#### Scenario: 清理临时文件
- **WHEN** 所有处理完成后
- **THEN** 删除本地临时目录中的所有下载文件

### Requirement: 记忆源文件删除处理（AI 服务 Python）
系统 SHALL 在记忆源文件被删除后，异步更新记忆内容和向量库。

#### Scenario: 删除源文件后更新记忆
- **WHEN** AI 服务收到删除文件请求
- **THEN** 读取现有 {memoryId}.md
- **AND** 找到该文件对应的记忆细节段落并删除
- **AND** 重新生成摘要（因内容变化）
- **AND** 更新元数据和细节
- **AND** 更新向量库中的摘要向量
- **AND** 上传新 md 文件覆盖原有文件

### Requirement: 记忆主题删除处理（AI 服务 Python）
系统 SHALL 在记忆主题被删除后，清理所有关联数据。

#### Scenario: 删除整个记忆主题
- **WHEN** AI 服务收到删除记忆请求
- **THEN** 删除对象存储中 /memory/{userId}/{roleId}/{memoryId}/ 目录下所有文件
- **AND** 删除向量库中所有关联记录

### Requirement: 对话模块记忆检索（AI 服务 Python）
系统 SHALL 在对话时根据对话内容检索相关记忆，辅助 LLM 生成回复。

#### Scenario: 对话中检索记忆
- **WHEN** 用户发送消息
- **THEN** 根据对话内容生成向量
- **AND** 在向量库中检索 Top5 相关记忆摘要
- **AND** 将 Top5 摘要提供给 LLM 辅助生成回复

#### Scenario: 追问记忆细节
- **WHEN** 用户追问某个记忆的细节
- **THEN** 根据对话内容定位到具体 memoryId
- **AND** 获取该 memory 的 {memoryId}.md 文件
- **AND** 提取其中的元数据 + 记忆细节 + 主观描述
- **AND** 可结合其他记忆的摘要（如 A 记忆细节 + B 记忆摘要）
- **AND** 提供给 LLM 生成响应

### Requirement: 对话记忆管理（AI 服务 Python）
系统 SHALL 维护对话记忆（短期 + 长期），使用遗忘机制管理，与回忆记忆隔离。

#### Scenario: 对话记忆与回忆记忆隔离
- **WHEN** 系统处理多轮对话
- **THEN** 对话记忆独立存储，不修改任何回忆记忆（{memoryId}.md）
- **AND** 对话记忆仅在当前会话上下文中使用

#### Scenario: 对话记忆形成长期记忆
- **WHEN** 多轮对话积累到一定阈值
- **THEN** LLM 判断是否需要将对话记忆转化为长期对话记忆
- **AND** 长期对话记忆存储但不影响回忆记忆

#### Scenario: 对话记忆遗忘机制
- **WHEN** 对话记忆存在时间超过阈值或使用频率/权重低于阈值
- **THEN** 对话记忆自动衰减或删除
- **AND** 回忆记忆（{memoryId}.md）永不遗忘

### Requirement: memory.md 生成 Skill
系统 SHALL 提供 memory.md 生成 Skill，当需要根据记忆源文件生成结构化记忆文件时调用。

#### Scenario: 调用 Skill 生成记忆文件
- **WHEN** AI 服务需要生成 {memoryId}.md
- **THEN** 调用 memory-generator Skill
- **AND** Skill 根据源文件解析结果和元数据，按模板生成 Markdown 文件

### Requirement: 记忆文件编辑状态管理（AI 服务 Python）
系统 SHALL 管理记忆文件的编辑状态，防止并发写入冲突。

#### Scenario: 写入锁定
- **WHEN** AI 服务开始写入 {memoryId}.md
- **THEN** 将该记忆文件的编辑状态设置为"写入中"
- **AND** 其他写入请求阻塞等待

#### Scenario: 写入完成释放
- **WHEN** AI 服务完成写入
- **THEN** 将编辑状态设置为"空闲"
- **AND** 唤醒等待队列中的下一个写入请求

### Requirement: 对象存储路径规范
系统 SHALL 使用统一的对象存储路径规范。

#### Scenario: 路径格式
- **WHEN** 存储记忆相关文件
- **THEN** 路径格式为 /memory/{userId}/{roleId}/{memoryId}/
- **AND** 该目录下存储所有记忆源文件 + {memoryId}.md

### Requirement: 数据库表结构设计
系统 SHALL 设计简洁合理的数据库表结构。

#### Scenario: 记忆主题表
- **WHEN** 创建记忆主题
- **THEN** 存储字段：id、memory_id（无连字符UUID）、user_id、role_id、theme_name（主题名称）、subjective_desc（主观描述）、status（状态：processing/completed/editing）、created_at、updated_at

#### Scenario: 记忆文件表
- **WHEN** 保存记忆源文件
- **THEN** 存储字段：id、memory_id（关联记忆主题）、file_key（对象存储key）、file_type（文件类型：text/audio/video/image）、file_name（原始文件名）、file_size（文件大小）、created_at

### Requirement: 记忆管理页面数据列表
系统 SHALL 在记忆管理页面展示记忆主题列表，并支持查看、编辑、删除操作。

#### Scenario: 数据列表展示
- **WHEN** 用户进入记忆管理页面
- **THEN** 展示记忆主题列表，包含：主题名称、文件数量、创建时间、状态
- **AND** 每行提供"查看"、"编辑"、"删除"操作按钮

---

## 设计优化补充

### Requirement: 上传路径前缀配置化
系统 SHALL 将对象存储上传路径前缀设计为可配置项，便于不同环境切换。

### Requirement: 文件类型校验（前端 + 后端）
系统 SHALL 在前端和后端同时校验文件类型和大小，前端提供友好提示，后端作为安全防线。

### Requirement: 接口幂等性
系统 SHALL 保证记忆保存接口的幂等性，使用 memoryId 作为幂等键，防止重复提交。

### Requirement: 日志与监控
系统 SHALL 在所有关键操作节点记录结构化日志，包括：上传开始/完成/失败、AI 解析开始/完成/失败、数据库操作、向量库操作。