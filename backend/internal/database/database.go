package database

import (
	"fmt"
	"os"
	"path/filepath"

	"echo-memory/internal/model"

	"go.uber.org/zap"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	gormLogger "gorm.io/gorm/logger"
)

// DB 全局数据库实例
var DB *gorm.DB

// Init 初始化数据库连接
func Init(dsn string, logger *zap.Logger) error {
	// 确保数据库文件所在目录存在
	dir := filepath.Dir(dsn)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("创建数据库目录失败: %w", err)
	}

	db, err := gorm.Open(sqlite.Open(dsn), &gorm.Config{
		Logger: gormLogger.Default.LogMode(gormLogger.Info),
	})
	if err != nil {
		return fmt.Errorf("连接数据库失败: %w", err)
	}

	// 启用 WAL 模式，提升并发读写性能
	if err := db.Exec("PRAGMA journal_mode=WAL").Error; err != nil {
		return fmt.Errorf("启用 WAL 模式失败: %w", err)
	}

	// 启用外键约束
	if err := db.Exec("PRAGMA foreign_keys=ON").Error; err != nil {
		return fmt.Errorf("启用外键约束失败: %w", err)
	}

	DB = db

	// 自动迁移
	if err := db.AutoMigrate(&model.MemoryTheme{}, &model.MemoryFile{}); err != nil {
		return fmt.Errorf("数据库迁移失败: %w", err)
	}
	logger.Info("数据库迁移完成")

	logger.Info("数据库初始化成功", zap.String("dsn", dsn))
	return nil
}

// Close 关闭数据库连接
func Close() error {
	if DB != nil {
		sqlDB, err := DB.DB()
		if err != nil {
			return err
		}
		return sqlDB.Close()
	}
	return nil
}