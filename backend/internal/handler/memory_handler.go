package handler

import (
	"strconv"

	"echo-memory/internal/client"
	"echo-memory/internal/service"
	"echo-memory/pkg/response"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

type MemoryHandler struct {
	svc    *service.MemoryService
	logger *zap.Logger
}

func NewMemoryHandler(svc *service.MemoryService, logger *zap.Logger) *MemoryHandler {
	return &MemoryHandler{svc: svc, logger: logger}
}

// ApplyMemoryID 申请记忆 ID
// POST /api/memory/apply-id
func (h *MemoryHandler) ApplyMemoryID(c *gin.Context) {
	memoryID := h.svc.GenerateMemoryID()
	h.logger.Info("生成记忆ID", zap.String("memory_id", memoryID))
	response.Success(c, gin.H{"memory_id": memoryID})
}

// CheckTheme 校验记忆主题唯一性
// GET /api/memory/check-theme?user_id=xxx&role_id=xxx&theme_name=xxx
func (h *MemoryHandler) CheckTheme(c *gin.Context) {
	userID := c.Query("user_id")
	roleID := c.Query("role_id")
	themeName := c.Query("theme_name")

	if userID == "" || roleID == "" || themeName == "" {
		response.BadRequest(c, "参数不完整")
		return
	}

	exists, err := h.svc.CheckThemeExists(userID, roleID, themeName)
	if err != nil {
		h.logger.Error("校验主题名称失败", zap.Error(err))
		response.InternalError(c, "校验失败")
		return
	}

	response.Success(c, gin.H{"exists": exists})
}

// SaveMemory 保存记忆
// POST /api/memory/save
func (h *MemoryHandler) SaveMemory(c *gin.Context) {
	var req struct {
		UserID         string                `json:"user_id" binding:"required"`
		RoleID         string                `json:"role_id" binding:"required"`
		MemoryID       string                `json:"memory_id" binding:"required"`
		ThemeName      string                `json:"theme_name" binding:"required"`
		SubjectiveDesc string                `json:"subjective_desc"`
		Files          []client.MemoryFileInfo `json:"files" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "参数错误: "+err.Error())
		return
	}

	if len(req.Files) == 0 {
		response.BadRequest(c, "至少需要上传一个文件")
		return
	}

	if err := h.svc.SaveMemory(req.UserID, req.RoleID, req.ThemeName, req.SubjectiveDesc, req.MemoryID, req.Files); err != nil {
		h.logger.Error("保存记忆失败", zap.Error(err))
		response.InternalError(c, err.Error())
		return
	}

	response.Success(c, gin.H{"memory_id": req.MemoryID})
}

// DeleteFile 删除单个记忆文件
// DELETE /api/memory/file?memory_id=xxx&file_id=xxx
func (h *MemoryHandler) DeleteFile(c *gin.Context) {
	memoryID := c.Query("memory_id")
	fileIDStr := c.Query("file_id")

	if memoryID == "" || fileIDStr == "" {
		response.BadRequest(c, "参数不完整")
		return
	}

	fileID, err := strconv.ParseUint(fileIDStr, 10, 64)
	if err != nil {
		response.BadRequest(c, "file_id 格式错误")
		return
	}

	if err := h.svc.DeleteFile(memoryID, uint(fileID)); err != nil {
		h.logger.Error("删除文件失败", zap.Error(err))
		response.InternalError(c, err.Error())
		return
	}

	response.Success(c, nil)
}

// DeleteTheme 删除整个记忆主题
// DELETE /api/memory/theme?memory_id=xxx
func (h *MemoryHandler) DeleteTheme(c *gin.Context) {
	memoryID := c.Query("memory_id")
	if memoryID == "" {
		response.BadRequest(c, "memory_id 不能为空")
		return
	}

	if err := h.svc.DeleteTheme(memoryID); err != nil {
		h.logger.Error("删除主题失败", zap.Error(err))
		response.InternalError(c, err.Error())
		return
	}

	response.Success(c, nil)
}

// ListThemes 查询记忆列表
// GET /api/memory/list?user_id=xxx&role_id=xxx&page=1&page_size=10
func (h *MemoryHandler) ListThemes(c *gin.Context) {
	userID := c.Query("user_id")
	roleID := c.Query("role_id")

	if userID == "" || roleID == "" {
		response.BadRequest(c, "参数不完整")
		return
	}

	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "10"))

	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 10
	}

	themes, total, err := h.svc.ListThemes(userID, roleID, page, pageSize)
	if err != nil {
		h.logger.Error("查询记忆列表失败", zap.Error(err))
		response.InternalError(c, "查询失败")
		return
	}

	// 构建返回数据，计算文件数量
	type ThemeItem struct {
		MemoryID       string `json:"memory_id"`
		ThemeName      string `json:"theme_name"`
		SubjectiveDesc string `json:"subjective_desc"`
		Status         string `json:"status"`
		FileCount      int    `json:"file_count"`
		CreatedAt      string `json:"created_at"`
		UpdatedAt      string `json:"updated_at"`
	}

	var items []ThemeItem
	for _, t := range themes {
		items = append(items, ThemeItem{
			MemoryID:       t.MemoryID,
			ThemeName:      t.ThemeName,
			SubjectiveDesc: t.SubjectiveDesc,
			Status:         t.Status,
			FileCount:      len(t.Files),
			CreatedAt:      t.CreatedAt.Format("2006-01-02 15:04:05"),
			UpdatedAt:      t.UpdatedAt.Format("2006-01-02 15:04:05"),
		})
	}

	response.Success(c, gin.H{
		"list":      items,
		"total":     total,
		"page":      page,
		"page_size": pageSize,
	})
}

// GetThemeDetail 查询记忆详情
// GET /api/memory/detail?memory_id=xxx
func (h *MemoryHandler) GetThemeDetail(c *gin.Context) {
	memoryID := c.Query("memory_id")
	if memoryID == "" {
		response.BadRequest(c, "memory_id 不能为空")
		return
	}

	theme, err := h.svc.GetThemeDetail(memoryID)
	if err != nil {
		h.logger.Error("查询记忆详情失败", zap.Error(err))
		response.NotFound(c, "记忆主题不存在")
		return
	}

	response.Success(c, theme)
}

// GetThemeStatus 查询记忆编辑状态
// GET /api/memory/status?memory_id=xxx
func (h *MemoryHandler) GetThemeStatus(c *gin.Context) {
	memoryID := c.Query("memory_id")
	if memoryID == "" {
		response.BadRequest(c, "memory_id 不能为空")
		return
	}

	status, err := h.svc.GetThemeStatus(memoryID)
	if err != nil {
		h.logger.Error("查询编辑状态失败", zap.Error(err))
		response.NotFound(c, "记忆主题不存在")
		return
	}

	response.Success(c, gin.H{"status": status})
}