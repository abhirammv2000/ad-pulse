package services

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"

	"cloud.google.com/go/pubsub"
	"github.com/gin-gonic/gin"
	"github.com/nedpals/supabase-go"
	"google.golang.org/api/option"
)

var projectID = "ad-pulse-team1"
var clkTopicID = "click-service-topic"
var keyFilePath = "./ad-pulse-team1-dbdee446d2a9.json"

const ()

func ClickServiceHandler(supabaseClient *supabase.Client) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		iId := ctx.Query("iid")
		fmt.Println("iId: ", iId)
		decodedIId, err := base64.StdEncoding.DecodeString(iId)
		if err != nil {
			ctx.String(http.StatusBadRequest, "Error decoding base64: %s", err.Error())
			return
		}

		var iidJSON map[string]interface{}

		err = json.Unmarshal(decodedIId, &iidJSON)
		if err != nil {
			fmt.Println("Error unmarshaling JSON:", err)
			return
		}

		decodedIIdString := string(decodedIId)

		err = PushToKafka(decodedIIdString, clkTopicID)
		if err != nil {
			fmt.Println("Error pushing to Kafka: ", err)
		}

		ctx.String(http.StatusOK, "Successfully pushed to Kafka")
	}
}

func PushToKafka(iid string, topicID string) error {
	ctx := context.Background()
	client, err := pubsub.NewClient(ctx, projectID, option.WithCredentialsFile(keyFilePath))
	if err != nil {
		return fmt.Errorf("pubsub.NewClient: %w", err)
	}
	defer client.Close()

	t := client.Topic(topicID)
	result := t.Publish(ctx, &pubsub.Message{
		Data: []byte(iid),
		Attributes: map[string]string{
			"origin":   "golang",
			"username": "gcp",
		},
	})
	id, err := result.Get(ctx)
	if err != nil {
		return fmt.Errorf("get: %w", err)
	}
	fmt.Println("Published message with custom attributes; msg ID: ", id)
	return nil
}
