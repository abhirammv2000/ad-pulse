package cache

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/redis/go-redis/v9"
)

// ErrNotFound means the key is not in the cache. It is what a cold cache
// looks like before the first refresh.
var ErrNotFound = errors.New("key not found in cache")

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
	value, err := store.rdb.Get(context.Background(), key).Result()
	if errors.Is(err, redis.Nil) {
		return "", ErrNotFound
	}
	return value, err
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
