package cache

import (
	"context"
	"encoding/json"

	"github.com/redis/go-redis/v9"
)

type Store interface {
	Get(key string) (string, error)
	Set(key string, value string) error
	Scan(pattern string) ([]string, error)
	HGetAll(key string) (map[string]string, error)
	GetCreatives(creativeID string) (*Creative, error)
}

type RedisStore struct {
	rdb *redis.Client
}

func NewRedisStore(rdb *redis.Client) Store {
	return &RedisStore{rdb: rdb}
}

func (store *RedisStore) Get(key string) (string, error) {
	return store.rdb.Get(context.Background(), key).Result()
}

func (store *RedisStore) Set(key string, value string) error {
	return store.rdb.Set(context.Background(), key, value, 0).Err()
}

func (store *RedisStore) Scan(pattern string) ([]string, error) {
	var keys []string
	iter := store.rdb.Scan(context.Background(), 0, "prefix:*", 0).Iterator()
	for iter.Next(context.Background()) {
		keys = append(keys, iter.Val())
	}
	if err := iter.Err(); err != nil {
		return nil, err
	}
	return keys, nil
}

func (store *RedisStore) HGetAll(key string) (map[string]string, error) {
	return store.rdb.HGetAll(context.Background(), key).Result()
}

func (store *RedisStore) GetCreatives(creativeID string) (*Creative, error) {
	var creativeJson Creative
	creative, err := store.Get(creativeID)
	if err != nil {
		return nil, err
	}
	json.Unmarshal([]byte(creative), &creativeJson)
	return &creativeJson, nil
}
