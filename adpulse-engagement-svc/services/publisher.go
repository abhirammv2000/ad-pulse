package services

import (
	"context"
	"fmt"
	"os"
	"sync"

	"cloud.google.com/go/pubsub"
	"google.golang.org/api/option"
)

// Publisher is the slice of Pub/Sub the engagement handlers need. Keeping it an
// interface lets the handler tests run without touching GCP.
type Publisher interface {
	Publish(ctx context.Context, topicID string, payload []byte) (string, error)
	Close() error
}

type pubSubPublisher struct {
	client *pubsub.Client

	// Handlers call Publish from many goroutines, so the topic map needs the lock.
	mu     sync.Mutex
	topics map[string]*pubsub.Topic
}

// NewPubSubPublisher builds a single long-lived Pub/Sub client.
//
// Credentials come from Application Default Credentials; on GKE that is the
// workload identity of the pod. Set GOOGLE_APPLICATION_CREDENTIALS to a key
// file path only for local development.
func NewPubSubPublisher() (Publisher, error) {
	projectID := os.Getenv("GCP_PROJECT_ID")
	if projectID == "" {
		return nil, fmt.Errorf("GCP_PROJECT_ID is not set")
	}

	ctx := context.Background()
	var opts []option.ClientOption
	if keyFile := os.Getenv("GOOGLE_APPLICATION_CREDENTIALS"); keyFile != "" {
		opts = append(opts, option.WithCredentialsFile(keyFile))
	}

	client, err := pubsub.NewClient(ctx, projectID, opts...)
	if err != nil {
		return nil, fmt.Errorf("pubsub.NewClient: %w", err)
	}
	return &pubSubPublisher{client: client, topics: make(map[string]*pubsub.Topic)}, nil
}

// topicFor returns the topic handle for an id, creating it on first use.
func (p *pubSubPublisher) topicFor(topicID string) *pubsub.Topic {
	p.mu.Lock()
	defer p.mu.Unlock()

	topic, ok := p.topics[topicID]
	if !ok {
		topic = p.client.Topic(topicID)
		p.topics[topicID] = topic
	}
	return topic
}

func (p *pubSubPublisher) Publish(ctx context.Context, topicID string, payload []byte) (string, error) {
	result := p.topicFor(topicID).Publish(ctx, &pubsub.Message{
		Data:       payload,
		Attributes: map[string]string{"origin": "adpulse-engagement-svc"},
	})
	return result.Get(ctx)
}

func (p *pubSubPublisher) Close() error {
	p.mu.Lock()
	defer p.mu.Unlock()

	for _, topic := range p.topics {
		topic.Stop()
	}
	return p.client.Close()
}

func topicID(envKey, fallback string) string {
	if v := os.Getenv(envKey); v != "" {
		return v
	}
	return fallback
}
