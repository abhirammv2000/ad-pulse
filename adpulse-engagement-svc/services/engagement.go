package services

import (
	"encoding/base64"
	"encoding/json"
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
)

// engagementHandler records one engagement event.
//
// The ad server hands the browser a URL carrying `iid`: a base64-encoded JSON
// blob identifying the ad, creative, campaign and advertiser. We validate it and
// forward it to the Pub/Sub topic that the subscriber service aggregates from.
func engagementHandler(publisher Publisher, topic string) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		decoded, err := base64.StdEncoding.DecodeString(ctx.Query("iid"))
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": "iid is not valid base64"})
			return
		}

		// Decode to confirm the payload is well-formed before publishing;
		// the subscriber would otherwise fail on every redelivery.
		var iid map[string]interface{}
		if err := json.Unmarshal(decoded, &iid); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": "iid is not valid JSON"})
			return
		}

		if _, err := publisher.Publish(ctx.Request.Context(), topic, decoded); err != nil {
			log.Printf("publish to %s failed: %v", topic, err)
			ctx.JSON(http.StatusBadGateway, gin.H{"error": "could not record engagement"})
			return
		}

		ctx.JSON(http.StatusOK, gin.H{"status": "recorded"})
	}
}

// ClickServiceHandler records a click on a served ad.
func ClickServiceHandler(publisher Publisher) gin.HandlerFunc {
	return engagementHandler(publisher, topicID("CLICK_TOPIC_ID", "click-service-topic"))
}

// CSCServiceHandler records a creative-successfully-called (render) event.
func CSCServiceHandler(publisher Publisher) gin.HandlerFunc {
	return engagementHandler(publisher, topicID("CSC_TOPIC_ID", "csc-service-topic"))
}
