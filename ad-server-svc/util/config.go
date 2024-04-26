package util

import (
	"github.com/spf13/viper"
)

type Config struct {
	DBDriver         string `mapstructure:"DB_DRIVER"`
	DBSource         string `mapstructure:"DB_SOURCE"`
	ServerAddress    string `mapstructure:"SERVER_ADDRESS"`
	AdManagerAddress string `mapstructure:"AD_MANAGER_ADDRESS"`
	RedisHost        string `mapstructure:"REDIS_HOST"`
	RedisPort        string `mapstructure:"REDIS_PORT"`
	RedisUsername    string `mapstructure:"REDIS_USERNAME"`
	RedisPassword    string `mapstructure:"REDIS_PASSWORD"`
	ClickUrl         string `mapstructure:"CLICK_URL"`
	RenderUrl        string `mapstructure:"RENDER_URL"`
}

func LoadConfig(path string) (config Config, err error) {
	viper.AddConfigPath(path)
	viper.SetConfigName("app")
	viper.SetConfigType("env")

	viper.AutomaticEnv()

	err = viper.ReadInConfig()
	if err != nil {
		return
	}

	err = viper.Unmarshal(&config)
	return
}
