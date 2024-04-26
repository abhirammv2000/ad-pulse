package main

import (
	"net/http"
	"os"

	"adpulse-engagement-svc.com/services"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/knadh/koanf/v2"
	"github.com/nedpals/supabase-go"
)

var k = koanf.New(".")

func main() {
	router := gin.Default()

	// Supabase Connection
	supabaseUrl := getEnv("SUPABASE_URL", "https://htppxkcokqiphaqkpnjc.supabase.co")
	supabaseKey := getEnv("SUPABASE_KEY", "")
	supaClient := supabase.CreateClient(supabaseUrl, supabaseKey)

	config := cors.DefaultConfig()
	config.AllowOrigins = []string{"*"} // Change this to your allowed origins
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE"}
	router.Use(cors.New(config))

	// define router group
	engagementGroup := router.Group("/engagement")
	{
		engagementGroup.GET("/clk", services.ClickServiceHandler(supaClient))
		engagementGroup.GET("/csc", services.CSCServiceHandler(supaClient))
	}

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "ok",
		})
	})

	err := router.Run(":8081")
	defer panic(err)

}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}
