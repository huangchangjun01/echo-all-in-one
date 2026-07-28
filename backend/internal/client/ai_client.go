package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"go.uber.org/zap"
)

// AIClient AI 服务客户端
type AIClient struct {
	baseURL    string
	httpClient *http.Client
	logger     *zap.Logger
}

// MemoryFileInfo 记忆文件信息
type MemoryFileInfo struct {
	FileKey  string `json:"file_key"`
	FileType string `json:"file_type"`
	FileName string `json:"file_name"`
}

// ParseRequest 解析请求
type ParseRequest struct {
	UserID         string           `json:"user_id"`
	RoleID         string           `json:"role_id"`
	MemoryID       string           `json:"memory_id"`
	ThemeName      string           `json:"theme_name"`
	SubjectiveDesc string           `json:"subjective_desc"`
	Files          []MemoryFileInfo `json:"files"`
}

// FileDeleteRequest 文件删除请求
type FileDeleteRequest struct {
	UserID   string `json:"user_id"`
	RoleID   string `json:"role_id"`
	MemoryID string `json:"memory_id"`
	FileKey  string `json:"file_key"`
	FileName string `json:"file_name"`
}

// ThemeDeleteRequest 主题删除请求
type ThemeDeleteRequest struct {
	UserID   string `json:"user_id"`
	RoleID   string `json:"role_id"`
	MemoryID string `json:"memory_id"`
}

// NewAIClient 创建 AI 客户端
func NewAIClient(baseURL string, logger *zap.Logger) *AIClient {
	return &AIClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		logger: logger,
	}
}

// CallParse 异步调用记忆解析接口
func (c *AIClient) CallParse(req *ParseRequest) {
	go func() {
		c.logger.Info("异步调用 AI 解析接口", zap.String("memory_id", req.MemoryID))
		body, _ := json.Marshal(req)
		resp, err := c.httpClient.Post(c.baseURL+"/api/ai/memory/parse", "application/json", bytes.NewReader(body))
		if err != nil {
			c.logger.Error("AI 解析接口调用失败", zap.Error(err), zap.String("memory_id", req.MemoryID))
			return
		}
		defer resp.Body.Close()
		respBody, _ := io.ReadAll(resp.Body)
		if resp.StatusCode != http.StatusOK {
			c.logger.Error("AI 解析接口返回错误", zap.Int("status", resp.StatusCode), zap.String("body", string(respBody)))
		} else {
			c.logger.Info("AI 解析接口调用成功", zap.String("memory_id", req.MemoryID))
		}
	}()
}

// CallFileDelete 异步调用文件删除接口
func (c *AIClient) CallFileDelete(req *FileDeleteRequest) {
	go func() {
		c.logger.Info("异步调用 AI 文件删除接口", zap.String("memory_id", req.MemoryID))
		body, _ := json.Marshal(req)
		resp, err := c.httpClient.Post(c.baseURL+"/api/ai/memory/file-delete", "application/json", bytes.NewReader(body))
		if err != nil {
			c.logger.Error("AI 文件删除接口调用失败", zap.Error(err))
			return
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			respBody, _ := io.ReadAll(resp.Body)
			c.logger.Error("AI 文件删除接口返回错误", zap.Int("status", resp.StatusCode), zap.String("body", string(respBody)))
		} else {
			c.logger.Info("AI 文件删除接口调用成功", zap.String("memory_id", req.MemoryID))
		}
	}()
}

// CallThemeDelete 异步调用主题删除接口
func (c *AIClient) CallThemeDelete(req *ThemeDeleteRequest) {
	go func() {
		c.logger.Info("异步调用 AI 主题删除接口", zap.String("memory_id", req.MemoryID))
		body, _ := json.Marshal(req)
		resp, err := c.httpClient.Post(c.baseURL+"/api/ai/memory/theme-delete", "application/json", bytes.NewReader(body))
		if err != nil {
			c.logger.Error("AI 主题删除接口调用失败", zap.Error(err))
			return
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			respBody, _ := io.ReadAll(resp.Body)
			c.logger.Error("AI 主题删除接口返回错误", zap.Int("status", resp.StatusCode), zap.String("body", string(respBody)))
		} else {
			c.logger.Info("AI 主题删除接口调用成功", zap.String("memory_id", req.MemoryID))
		}
	}()
}

// CheckHealth 检查 AI 服务健康状态
func (c *AIClient) CheckHealth(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, "GET", c.baseURL+"/api/ai/health", nil)
	if err != nil {
		return fmt.Errorf("创建健康检查请求失败: %w", err)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("AI 服务不可达: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("AI 服务健康检查失败: status=%d", resp.StatusCode)
	}
	return nil
}