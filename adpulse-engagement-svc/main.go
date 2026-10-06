package main

import (
	"log"
	"net/http"
	"os"

	"adpulse-engagement-svc.com/services"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func main() {
	publisher, err := services.NewPubSubPublisher()
	if err != nil {
		log.Fatal("cannot create pubsub publisher: ", err)
	}
	defer publisher.Close()

	if os.Getenv("TRACKING_SECRET") == "" {
		log.Println("TRACKING_SECRET is not set, so click and render URLs are not checked")
	}

	router := gin.Default()

	corsConfig := cors.DefaultConfig()
	corsConfig.AllowOrigins = []string{"*"} // open to every origin, restrict this before real use
	corsConfig.AllowMethods = []string{"GET", "POST", "PUT", "DELETE"}
	router.Use(cors.New(corsConfig))

	// click and render pings
	engagementGroup := router.Group("/engagement")
	{
		engagementGroup.GET("/clk", services.ClickServiceHandler(publisher))
		engagementGroup.GET("/csc", services.CSCServiceHandler(publisher))
	}

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	if err := router.Run(getEnv("SERVER_ADDRESS", ":8081")); err != nil {
		log.Fatal("cannot start server: ", err)
	}
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}
