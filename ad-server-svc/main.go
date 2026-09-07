package main

import (
	"log"
	"net"

	"adserver/api"
	"adserver/cache"
	"adserver/util"

	"github.com/redis/go-redis/v9"
)

func main() {
	config, err := util.LoadConfig(".")
	if err != nil {
		log.Fatal("cannot load configuration: ", err)
	}

	rdb := redis.NewClient(&redis.Options{
		Addr:     net.JoinHostPort(config.RedisHost, config.RedisPort),
		Username: config.RedisUsername,
		Password: config.RedisPassword,
	})

	store := cache.NewRedisStore(rdb)

	server, err := api.NewServer(config, store)
	if err != nil {
		log.Fatal("cannot create server: ", err)
	}

	if err := server.Start(config.ServerAddress); err != nil {
		log.Fatal("cannot start server: ", err)
	}
}
