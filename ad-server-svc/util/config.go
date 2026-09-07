package util

import (
	"errors"

	"github.com/spf13/viper"
)

type Config struct {
	ServerAddress    string `mapstructure:"SERVER_ADDRESS"`
	AdManagerAddress string `mapstructure:"AD_MANAGER_ADDRESS"`
	RedisHost        string `mapstructure:"REDIS_HOST"`
	RedisPort        string `mapstructure:"REDIS_PORT"`
	RedisUsername    string `mapstructure:"REDIS_USERNAME"`
	RedisPassword    string `mapstructure:"REDIS_PASSWORD"`
	ClickUrl         string `mapstructure:"CLICK_URL"`
	RenderUrl        string `mapstructure:"RENDER_URL"`
}

// defaults doubles as the list of keys viper will read from the environment:
// AutomaticEnv only resolves keys viper already knows about, so every field
// must be registered here for the env var to take effect.
var defaults = map[string]string{
	"SERVER_ADDRESS":     "0.0.0.0:8080",
	"AD_MANAGER_ADDRESS": "http://localhost:5000",
	"REDIS_HOST":         "localhost",
	"REDIS_PORT":         "6379",
	"REDIS_USERNAME":     "",
	"REDIS_PASSWORD":     "",
	"CLICK_URL":          "http://localhost:8081/engagement/clk",
	"RENDER_URL":         "http://localhost:8081/engagement/csc",
}

// LoadConfig reads configuration from app.env in path, falling back to
// environment variables. The file is optional — in Kubernetes the whole config
// arrives through the environment.
func LoadConfig(path string) (config Config, err error) {
	viper.AddConfigPath(path)
	viper.SetConfigName("app")
	viper.SetConfigType("env")

	for key, value := range defaults {
		viper.SetDefault(key, value)
	}
	viper.AutomaticEnv()

	if err = viper.ReadInConfig(); err != nil {
		var notFound viper.ConfigFileNotFoundError
		if !errors.As(err, &notFound) {
			return
		}
		err = nil
	}

	err = viper.Unmarshal(&config)
	return
}
