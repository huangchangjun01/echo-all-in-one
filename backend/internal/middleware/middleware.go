package middleware

import (
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// RequestID 为每个请求生成唯一 ID 并注入 context
func RequestID() gin.HandlerFunc {
	return func(c *gin.Context) {
		requestID := uuid.New().String()
		c.Set("RequestID", requestID)
		c.Header("X-Request-ID", requestID)
		c.Next()
	}
}

// Logger 使用 zap 记录请求日志
func Logger(logger *zap.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		c.Next()

		latency := time.Since(start)
		statusCode := c.Writer.Status()
		clientIP := c.ClientIP()
		method := c.Request.Method
		requestID, _ := c.Get("RequestID")

		fields := []zap.Field{
			zap.Int("status", statusCode),
			zap.String("method", method),
			zap.String("path", path),
			zap.String("query", query),
			zap.String("ip", clientIP),
			zap.Duration("latency", latency),
			zap.Any("request_id", requestID),
		}

		if statusCode >= 500 {
			logger.Error("请求处理失败", fields...)
		} else if statusCode >= 400 {
			logger.Warn("客户端请求错误", fields...)
		} else {
			logger.Info("请求处理完成", fields...)
		}
	}
}

// Recovery 自定义 panic 恢复中间件
func Recovery(logger *zap.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if err := recover(); err != nil {
				requestID, _ := c.Get("RequestID")
				logger.Error("服务 panic 恢复",
					zap.Any("error", err),
					zap.Any("request_id", requestID),
					zap.String("path", c.Request.URL.Path),
					zap.String("method", c.Request.Method),
				)
				c.AbortWithStatusJSON(500, gin.H{
					"code":    500,
					"message": "内部服务错误",
					"data":    nil,
				})
			}
		}()
		c.Next()
	}
}