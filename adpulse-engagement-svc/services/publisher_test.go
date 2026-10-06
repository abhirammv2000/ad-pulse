package services

import (
	"context"
	"fmt"
	"sync"
	"testing"

	"cloud.google.com/go/pubsub"
)

// newOfflinePublisher builds a publisher whose client never leaves the machine:
// with PUBSUB_EMULATOR_HOST set, the client does not connect or authenticate
// until something is actually published.
func newOfflinePublisher(t *testing.T) *pubSubPublisher {
	t.Helper()
	t.Setenv("PUBSUB_EMULATOR_HOST", "localhost:1")
	client, err := pubsub.NewClient(context.Background(), "test-project")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { client.Close() })
	return &pubSubPublisher{client: client, topics: make(map[string]*pubsub.Topic)}
}

// Handlers run on many goroutines at once. Run this with -race: the topic map
// used to be read and written with no lock.
func TestTopicLookupIsSafeForConcurrentUse(t *testing.T) {
	publisher := newOfflinePublisher(t)

	var wg sync.WaitGroup
	for i := 0; i < 64; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			publisher.topicFor(fmt.Sprintf("topic-%d", i%4))
		}(i)
	}
	wg.Wait()

	if got := len(publisher.topics); got != 4 {
		t.Errorf("created %d topic handles for 4 topic ids", got)
	}
}

func TestTheSameTopicIdGivesTheSameHandle(t *testing.T) {
	publisher := newOfflinePublisher(t)

	if publisher.topicFor("clicks") != publisher.topicFor("clicks") {
		t.Error("a second lookup created a new handle instead of reusing the first")
	}
}
