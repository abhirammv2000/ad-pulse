package cache

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/redis/go-redis/v9"
)

type Store interface {
	Get(key string) (string, error)
	Set(key string, value string) error
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

func (store *RedisStore) HGetAll(key string) (map[string]string, error) {
	return store.rdb.HGetAll(context.Background(), key).Result()
}

func (store *RedisStore) GetCreatives(creativeID string) (*Creative, error) {
	creative, err := store.Get(creativeID)
	if err != nil {
		return nil, err
	}
	var creativeJson Creative
	if err := json.Unmarshal([]byte(creative), &creativeJson); err != nil {
		return nil, fmt.Errorf("decoding creative %s: %w", creativeID, err)
	}
	return &creativeJson, nil
}
