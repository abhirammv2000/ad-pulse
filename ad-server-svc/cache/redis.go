package cache

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"

	"github.com/redis/go-redis/v9"
)

// ErrNotFound means the key is not in the cache. It is what a cold cache
// looks like before the first refresh.
var ErrNotFound = errors.New("key not found in cache")

// Store is the serving cache. Every call takes the request's context, so a slow
// Redis can't hold a request past its deadline.
type Store interface {
	Get(ctx context.Context, key string) (string, error)
	Set(ctx context.Context, key string, value string) error
	HGetAll(ctx context.Context, key string) (map[string]string, error)
	GetCreatives(ctx context.Context, creativeID string) (*Creative, error)
	// MGet reads many keys in one round trip. A missing key comes back as "".
	MGet(ctx context.Context, keys []string) ([]string, error)
	// CountSince counts, for each query, the members of a sorted set scored above
	// Since, all in one round trip. A missing set counts 0.
	CountSince(ctx context.Context, queries []CountQuery) ([]int64, error)
}

// CountQuery asks how many members of the sorted set at Key have a score greater than Since.
type CountQuery struct {
	Key   string
	Since int64
}

type RedisStore struct {
	rdb *redis.Client
}

func NewRedisStore(rdb *redis.Client) Store {
	return &RedisStore{rdb: rdb}
}

func (store *RedisStore) Get(ctx context.Context, key string) (string, error) {
	value, err := store.rdb.Get(ctx, key).Result()
	if errors.Is(err, redis.Nil) {
		return "", ErrNotFound
	}
	return value, err
}

func (store *RedisStore) Set(ctx context.Context, key string, value string) error {
	return store.rdb.Set(ctx, key, value, 0).Err()
}

func (store *RedisStore) HGetAll(ctx context.Context, key string) (map[string]string, error) {
	return store.rdb.HGetAll(ctx, key).Result()
}

func (store *RedisStore) MGet(ctx context.Context, keys []string) ([]string, error) {
	values, err := store.rdb.MGet(ctx, keys...).Result()
	if err != nil {
		return nil, err
	}
	out := make([]string, len(values))
	for i, value := range values {
		if text, ok := value.(string); ok {
			out[i] = text
		}
	}
	return out, nil
}

func (store *RedisStore) CountSince(ctx context.Context, queries []CountQuery) ([]int64, error) {
	pipe := store.rdb.Pipeline()
	commands := make([]*redis.IntCmd, len(queries))
	for i, query := range queries {
		// "(" makes the lower bound exclusive: an event exactly one window ago is outside it.
		commands[i] = pipe.ZCount(ctx, query.Key, "("+strconv.FormatInt(query.Since, 10), "+inf")
	}
	if _, err := pipe.Exec(ctx); err != nil {
		return nil, err
	}
	counts := make([]int64, len(queries))
	for i, command := range commands {
		counts[i] = command.Val()
	}
	return counts, nil
}

func (store *RedisStore) GetCreatives(ctx context.Context, creativeID string) (*Creative, error) {
	creative, err := store.Get(ctx, creativeID)
	if err != nil {
		return nil, err
	}
	var creativeJson Creative
	if err := json.Unmarshal([]byte(creative), &creativeJson); err != nil {
		return nil, fmt.Errorf("decoding creative %s: %w", creativeID, err)
	}
	return &creativeJson, nil
}
