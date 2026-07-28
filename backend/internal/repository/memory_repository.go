package repository

import (
	"echo-memory/internal/model"

	"gorm.io/gorm"
)

type MemoryRepository struct {
	db *gorm.DB
}

func NewMemoryRepository(db *gorm.DB) *MemoryRepository {
	return &MemoryRepository{db: db}
}

// CheckThemeExists 检查主题名称是否已存在
func (r *MemoryRepository) CheckThemeExists(userID, roleID, themeName string) (bool, error) {
	var count int64
	err := r.db.Model(&model.MemoryTheme{}).
		Where("user_id = ? AND role_id = ? AND theme_name = ?", userID, roleID, themeName).
		Count(&count).Error
	return count > 0, err
}

// CreateThemeWithFiles 事务创建记忆主题和文件
func (r *MemoryRepository) CreateThemeWithFiles(theme *model.MemoryTheme, files []model.MemoryFile) error {
	return r.db.Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(theme).Error; err != nil {
			return err
		}
		if len(files) > 0 {
			if err := tx.Create(&files).Error; err != nil {
				return err
			}
		}
		return nil
	})
}

// GetThemeByMemoryID 根据 memoryId 查询主题
func (r *MemoryRepository) GetThemeByMemoryID(memoryID string) (*model.MemoryTheme, error) {
	var theme model.MemoryTheme
	err := r.db.Where("memory_id = ?", memoryID).First(&theme).Error
	if err != nil {
		return nil, err
	}
	return &theme, nil
}

// GetThemeWithFiles 查询主题及关联文件
func (r *MemoryRepository) GetThemeWithFiles(memoryID string) (*model.MemoryTheme, error) {
	var theme model.MemoryTheme
	err := r.db.Preload("Files").Where("memory_id = ?", memoryID).First(&theme).Error
	if err != nil {
		return nil, err
	}
	return &theme, nil
}

// ListThemes 分页查询记忆主题列表
func (r *MemoryRepository) ListThemes(userID, roleID string, page, pageSize int) ([]model.MemoryTheme, int64, error) {
	var themes []model.MemoryTheme
	var total int64

	query := r.db.Model(&model.MemoryTheme{}).Where("user_id = ? AND role_id = ?", userID, roleID)

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	offset := (page - 1) * pageSize
	err := query.Preload("Files").Order("created_at DESC").Offset(offset).Limit(pageSize).Find(&themes).Error
	return themes, total, err
}

// DeleteFile 删除单个文件记录
func (r *MemoryRepository) DeleteFile(memoryID string, fileID uint) error {
	return r.db.Where("memory_id = ? AND id = ?", memoryID, fileID).Delete(&model.MemoryFile{}).Error
}

// GetFileByID 根据 ID 查询文件
func (r *MemoryRepository) GetFileByID(fileID uint) (*model.MemoryFile, error) {
	var file model.MemoryFile
	err := r.db.First(&file, fileID).Error
	if err != nil {
		return nil, err
	}
	return &file, nil
}

// DeleteThemeWithFiles 事务删除主题和所有关联文件
func (r *MemoryRepository) DeleteThemeWithFiles(memoryID string) error {
	return r.db.Transaction(func(tx *gorm.DB) error {
		if err := tx.Where("memory_id = ?", memoryID).Delete(&model.MemoryFile{}).Error; err != nil {
			return err
		}
		if err := tx.Where("memory_id = ?", memoryID).Delete(&model.MemoryTheme{}).Error; err != nil {
			return err
		}
		return nil
	})
}

// UpdateThemeStatus 更新主题状态
func (r *MemoryRepository) UpdateThemeStatus(memoryID, status string) error {
	return r.db.Model(&model.MemoryTheme{}).Where("memory_id = ?", memoryID).Update("status", status).Error
}

// UpdateTheme 更新主题信息（主观描述）
func (r *MemoryRepository) UpdateTheme(memoryID, subjectiveDesc string) error {
	return r.db.Model(&model.MemoryTheme{}).Where("memory_id = ?", memoryID).Update("subjective_desc", subjectiveDesc).Error
}

// AddFiles 批量添加文件
func (r *MemoryRepository) AddFiles(files []model.MemoryFile) error {
	return r.db.Create(&files).Error
}

// DeleteFilesByMemoryID 删除指定记忆主题下的所有文件
func (r *MemoryRepository) DeleteFilesByMemoryID(memoryID string) error {
	return r.db.Where("memory_id = ?", memoryID).Delete(&model.MemoryFile{}).Error
}