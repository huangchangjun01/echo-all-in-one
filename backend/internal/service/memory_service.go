package service

import (
	"fmt"
	"strings"

	"echo-memory/internal/client"
	"echo-memory/internal/model"
	"echo-memory/internal/repository"

	"github.com/google/uuid"
	"go.uber.org/zap"
)

type MemoryService struct {
	repo     *repository.MemoryRepository
	aiClient *client.AIClient
	logger   *zap.Logger
}

func NewMemoryService(repo *repository.MemoryRepository, aiClient *client.AIClient, logger *zap.Logger) *MemoryService {
	return &MemoryService{repo: repo, aiClient: aiClient, logger: logger}
}

// GenerateMemoryID 生成去除连字符的 UUID
func (s *MemoryService) GenerateMemoryID() string {
	return strings.ReplaceAll(uuid.New().String(), "-", "")
}

// CheckThemeExists 检查主题是否已存在
func (s *MemoryService) CheckThemeExists(userID, roleID, themeName string) (bool, error) {
	return s.repo.CheckThemeExists(userID, roleID, themeName)
}

// SaveMemory 保存记忆主题和文件
func (s *MemoryService) SaveMemory(userID, roleID, themeName, subjectiveDesc, memoryID string, files []client.MemoryFileInfo) error {
	// 构建文件模型
	var fileModels []model.MemoryFile
	for _, f := range files {
		fileModels = append(fileModels, model.MemoryFile{
			MemoryID: memoryID,
			FileKey:  f.FileKey,
			FileType: f.FileType,
			FileName: f.FileName,
			FileSize: 0,
		})
	}

	theme := &model.MemoryTheme{
		MemoryID:       memoryID,
		UserID:         userID,
		RoleID:         roleID,
		ThemeName:      themeName,
		SubjectiveDesc: subjectiveDesc,
		Status:         "processing",
	}

	// 事务写入
	if err := s.repo.CreateThemeWithFiles(theme, fileModels); err != nil {
		s.logger.Error("保存记忆失败", zap.Error(err))
		return fmt.Errorf("保存记忆失败: %w", err)
	}

	s.logger.Info("记忆保存成功", zap.String("memory_id", memoryID))

	// 异步调用 AI 解析
	s.aiClient.CallParse(&client.ParseRequest{
		UserID:         userID,
		RoleID:         roleID,
		MemoryID:       memoryID,
		ThemeName:      themeName,
		SubjectiveDesc: subjectiveDesc,
		Files:          files,
	})

	return nil
}

// ListThemes 查询记忆列表
func (s *MemoryService) ListThemes(userID, roleID string, page, pageSize int) ([]model.MemoryTheme, int64, error) {
	return s.repo.ListThemes(userID, roleID, page, pageSize)
}

// GetThemeDetail 查询记忆详情
func (s *MemoryService) GetThemeDetail(memoryID string) (*model.MemoryTheme, error) {
	return s.repo.GetThemeWithFiles(memoryID)
}

// GetThemeStatus 查询记忆编辑状态
func (s *MemoryService) GetThemeStatus(memoryID string) (string, error) {
	theme, err := s.repo.GetThemeByMemoryID(memoryID)
	if err != nil {
		return "", err
	}
	return theme.Status, nil
}

// DeleteFile 删除单个文件
func (s *MemoryService) DeleteFile(memoryID string, fileID uint) error {
	// 查询文件信息
	file, err := s.repo.GetFileByID(fileID)
	if err != nil {
		return fmt.Errorf("文件不存在: %w", err)
	}

	// 删除文件记录
	if err := s.repo.DeleteFile(memoryID, fileID); err != nil {
		return fmt.Errorf("删除文件记录失败: %w", err)
	}

	// 更新主题状态
	if err := s.repo.UpdateThemeStatus(memoryID, "editing"); err != nil {
		s.logger.Error("更新主题状态失败", zap.Error(err))
	}

	// 异步调用 AI 服务
	theme, err := s.repo.GetThemeByMemoryID(memoryID)
	if err != nil {
		s.logger.Error("获取主题信息失败", zap.Error(err))
	} else {
		s.aiClient.CallFileDelete(&client.FileDeleteRequest{
			UserID:   theme.UserID,
			RoleID:   theme.RoleID,
			MemoryID: memoryID,
			FileKey:  file.FileKey,
			FileName: file.FileName,
		})
	}

	s.logger.Info("文件删除成功", zap.String("memory_id", memoryID), zap.Uint("file_id", fileID))
	return nil
}

// DeleteTheme 删除整个记忆主题
func (s *MemoryService) DeleteTheme(memoryID string) error {
	// 获取主题信息
	theme, err := s.repo.GetThemeByMemoryID(memoryID)
	if err != nil {
		return fmt.Errorf("记忆主题不存在: %w", err)
	}

	// 事务删除
	if err := s.repo.DeleteThemeWithFiles(memoryID); err != nil {
		return fmt.Errorf("删除记忆主题失败: %w", err)
	}

	// 异步调用 AI 服务
	s.aiClient.CallThemeDelete(&client.ThemeDeleteRequest{
		UserID:   theme.UserID,
		RoleID:   theme.RoleID,
		MemoryID: memoryID,
	})

	s.logger.Info("记忆主题删除成功", zap.String("memory_id", memoryID))
	return nil
}