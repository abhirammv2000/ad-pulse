package services

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/nedpals/supabase-go"
)

var cscTopicID = "csc-service-topic"

func CSCServiceHandler(supabaseClient *supabase.Client) gin.HandlerFunc {
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

		err = PushToKafka(decodedIIdString, cscTopicID)
		if err != nil {
			fmt.Println("Error pushing to Kafka: ", err)
		}

		ctx.String(http.StatusOK, "Successfully pushed to Kafka")
	}
}
