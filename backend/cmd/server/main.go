package main

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"echo-memory/internal/client"
	"echo-memory/internal/config"
	"echo-memory/internal/database"
	"echo-memory/internal/handler"
	"echo-memory/internal/middleware"
	"echo-memory/internal/repository"
	"echo-memory/internal/service"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

func main() {
	// 初始化日志
	logger := initLogger()
	defer logger.Sync()

	// 加载配置
	cfg, err := config.Load("config/config.yaml")
	if err != nil {
		logger.Fatal("加载配置失败", zap.Error(err))
	}
	logger.Info("配置加载成功")

	// 初始化数据库
	if err := database.Init(cfg.Database.DSN, logger); err != nil {
		logger.Fatal("初始化数据库失败", zap.Error(err))
	}
	defer func() {
		if err := database.Close(); err != nil {
			logger.Error("关闭数据库连接失败", zap.Error(err))
		}
	}()

	// 设置 Gin 运行模式
	gin.SetMode(cfg.Server.Mode)

	// 初始化 Gin 引擎
	engine := gin.New()

	// 注册中间件
	engine.Use(
		middleware.RequestID(),
		middleware.Logger(logger),
		middleware.Recovery(logger),
	)

	// CORS 中间件
	engine.Use(cors.New(cors.Config{
		AllowAllOrigins:  true,
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization", "X-Request-ID"},
		ExposeHeaders:    []string{"Content-Length", "X-Request-ID"},
		AllowCredentials: true,
		MaxAge:           12 * 60 * 60,
	}))

	// 健康检查
	engine.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status": "ok",
		})
	})

	// 初始化各层
	aiClient := client.NewAIClient(cfg.AIService.BaseURL, logger)
	memoryRepo := repository.NewMemoryRepository(database.DB)
	memorySvc := service.NewMemoryService(memoryRepo, aiClient, logger)
	memoryHandler := handler.NewMemoryHandler(memorySvc, logger)

	// 注册记忆管理路由
	api := engine.Group("/api/memory")
	{
		api.POST("/apply-id", memoryHandler.ApplyMemoryID)
		api.GET("/check-theme", memoryHandler.CheckTheme)
		api.POST("/save", memoryHandler.SaveMemory)
		api.DELETE("/file", memoryHandler.DeleteFile)
		api.DELETE("/theme", memoryHandler.DeleteTheme)
		api.GET("/list", memoryHandler.ListThemes)
		api.GET("/detail", memoryHandler.GetThemeDetail)
		api.GET("/status", memoryHandler.GetThemeStatus)
	}

	// 启动 HTTP 服务
	addr := fmt.Sprintf(":%d", cfg.Server.Port)
	logger.Info("服务启动", zap.String("addr", addr))

	// 优雅关闭
	go func() {
		quit := make(chan os.Signal, 1)
		signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
		<-quit
		logger.Info("正在关闭服务...")
		os.Exit(0)
	}()

	if err := engine.Run(addr); err != nil {
		logger.Fatal("服务启动失败", zap.Error(err))
	}
}

// initLogger 初始化 zap 日志
func initLogger() *zap.Logger {
	encoderConfig := zap.NewProductionEncoderConfig()
	encoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	encoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder

	config := zap.Config{
		Level:            zap.NewAtomicLevelAt(zap.DebugLevel),
		Development:      true,
		Encoding:         "console",
		EncoderConfig:    encoderConfig,
		OutputPaths:      []string{"stdout"},
		ErrorOutputPaths: []string{"stderr"},
	}

	logger, err := config.Build()
	if err != nil {
		panic(fmt.Sprintf("初始化日志失败: %v", err))
	}

	return logger
}