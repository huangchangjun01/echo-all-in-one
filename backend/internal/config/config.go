package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

// Config 全局配置结构体
type Config struct {
	Server    ServerConfig    `yaml:"server"`
	Database  DatabaseConfig  `yaml:"database"`
	AIService AIServiceConfig `yaml:"ai_service"`
	Storage   StorageConfig   `yaml:"storage"`
	Log       LogConfig       `yaml:"log"`
}

// ServerConfig 服务配置
type ServerConfig struct {
	Port int    `yaml:"port"`
	Mode string `yaml:"mode"`
}

// DatabaseConfig 数据库配置
type DatabaseConfig struct {
	Driver string `yaml:"driver"`
	DSN    string `yaml:"dsn"`
}

// AIServiceConfig AI 服务配置
type AIServiceConfig struct {
	BaseURL string `yaml:"base_url"`
}

// StorageConfig 存储配置
type StorageConfig struct {
	Type      string `yaml:"type"`
	LocalPath string `yaml:"local_path"`
	BasePath  string `yaml:"base_path"`
}

// LogConfig 日志配置
type LogConfig struct {
	Level  string `yaml:"level"`
	Output string `yaml:"output"`
}

// Load 从指定路径加载 YAML 配置文件
func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	cfg := &Config{}
	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, err
	}

	return cfg, nil
}