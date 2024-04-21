package main

import (
	"log"

	"adserver/api"
	"adserver/cache"
	"adserver/util"

	_ "github.com/lib/pq"
	"github.com/redis/go-redis/v9"
)

func main() {
	config, err := util.LoadConfig(".")
	if err != nil {
		log.Fatal("cannot load configuration: ", err)
	}
	redisAddress := config.RedisHost + ":" + config.RedisPort
	rdb := redis.NewClient(&redis.Options{
		Addr:     redisAddress,
		Username: config.RedisUsername,
		Password: config.RedisPassword,
	})

	store := cache.NewRedisStore(rdb)

	server, err := api.NewServer(config, store)
	if err != nil {
		log.Fatal("cannot create server")
	}

	err = server.Start(config.ServerAddress)
	if err != nil {
		log.Fatal("Cannot start server: ", err)
	}
}
