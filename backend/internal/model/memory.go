package model

import "time"

// MemoryTheme 记忆主题表
type MemoryTheme struct {
	ID             uint         `gorm:"primaryKey;autoIncrement" json:"id"`
	MemoryID       string       `gorm:"type:varchar(64);uniqueIndex;not null;comment:记忆ID(无连字符UUID)" json:"memory_id"`
	UserID         string       `gorm:"type:varchar(64);index;not null;comment:用户ID" json:"user_id"`
	RoleID         string       `gorm:"type:varchar(64);index;not null;comment:角色ID" json:"role_id"`
	ThemeName      string       `gorm:"type:varchar(255);not null;comment:记忆主题名称" json:"theme_name"`
	SubjectiveDesc string       `gorm:"type:text;comment:主观描述" json:"subjective_desc"`
	Status         string       `gorm:"type:varchar(20);default:processing;comment:状态:processing/completed/editing" json:"status"`
	CreatedAt      time.Time    `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt      time.Time    `gorm:"autoUpdateTime" json:"updated_at"`
	Files          []MemoryFile `gorm:"foreignKey:MemoryID;references:MemoryID" json:"files,omitempty"`
}

func (MemoryTheme) TableName() string {
	return "memory_themes"
}

// MemoryFile 记忆文件表
type MemoryFile struct {
	ID        uint      `gorm:"primaryKey;autoIncrement" json:"id"`
	MemoryID  string    `gorm:"type:varchar(64);index;not null;comment:关联记忆主题ID" json:"memory_id"`
	FileKey   string    `gorm:"type:varchar(512);not null;comment:对象存储Key" json:"file_key"`
	FileType  string    `gorm:"type:varchar(20);not null;comment:文件类型:text/audio/video/image" json:"file_type"`
	FileName  string    `gorm:"type:varchar(255);not null;comment:原始文件名" json:"file_name"`
	FileSize  int64     `gorm:"type:bigint;default:0;comment:文件大小(字节)" json:"file_size"`
	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
}

func (MemoryFile) TableName() string {
	return "memory_files"
}