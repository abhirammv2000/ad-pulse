package services

import (
	"encoding/base64"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"
)

// maxEventAge is how long after an ad was served its click or render still
// counts. The subscriber stops counting at 48 hours and remembers what it has
// counted for 72, so an event replayed later can never be counted twice. See
// adpulse-engagement-subscriber-svc/app.py.
const maxEventAge = 24 * time.Hour

// maxClockSkew is how far in the future a serve time may be, because the ad
// server's clock and this one may not quite agree.
const maxClockSkew = 5 * time.Minute

// now is where the current time comes from. Tests replace it.
var now = time.Now

// servedBid is the part of an iid this service checks. The iid itself is
// published unchanged.
type servedBid struct {
	BidID    string `json:"bidid"`
	ServedAt int64  `json:"requesttimestamp"` // Unix seconds, set by the ad server
}

// engagementHandler records one engagement event.
//
// The ad server hands the browser a URL carrying `iid`: a base64-encoded JSON
// blob identifying the bid, ad, creative, campaign and advertiser, and when the
// ad was served. We validate it and forward it to the Pub/Sub topic that the
// subscriber service counts from. An event served too long ago gets a 410.
//
// When secret is not empty the URL must also carry a `sig` parameter, the HMAC
// of the iid text, or the request is refused. With an empty secret nothing is
// checked, which is only fine for local development.
func engagementHandler(publisher Publisher, topic, secret string) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		encodedIID := ctx.Query("iid")
		if secret != "" && !validSignature(secret, encodedIID, ctx.Query("sig")) {
			ctx.JSON(http.StatusForbidden, gin.H{"error": "invalid signature"})
			return
		}

		decoded, err := base64.StdEncoding.DecodeString(encodedIID)
		if err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": "iid is not valid base64"})
			return
		}

		// Decode to confirm the payload is well-formed before publishing;
		// the subscriber would otherwise fail on every redelivery.
		var bid servedBid
		if err := json.Unmarshal(decoded, &bid); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": "iid is not valid JSON"})
			return
		}
		if bid.BidID == "" || bid.ServedAt == 0 {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": "iid has no bid id or serve time"})
			return
		}
		age := now().Sub(time.Unix(bid.ServedAt, 0))
		if age > maxEventAge {
			ctx.JSON(http.StatusGone, gin.H{"error": "this ad was served too long ago to count"})
			return
		}
		if age < -maxClockSkew {
			ctx.JSON(http.StatusBadRequest, gin.H{"error": "iid has a serve time in the future"})
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
	return engagementHandler(publisher, topicID("CLICK_TOPIC_ID", "click-service-topic"), os.Getenv("TRACKING_SECRET"))
}

// CSCServiceHandler records a creative-successfully-called (render) event.
func CSCServiceHandler(publisher Publisher) gin.HandlerFunc {
	return engagementHandler(publisher, topicID("CSC_TOPIC_ID", "csc-service-topic"), os.Getenv("TRACKING_SECRET"))
}
