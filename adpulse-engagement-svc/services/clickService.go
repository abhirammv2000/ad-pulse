package services

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/nedpals/supabase-go"
)

func ClickServiceHandler(supabaseClient *supabase.Client) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var results any
		err := supabaseClient.DB.From("advertiser").Select("*").Execute(&results)
		if err != nil {
			ctx.IndentedJSON(http.StatusInternalServerError, gin.H{
				"status":  "error",
				"message": err.Error(),
			})
			return
		}
		fmt.Println("results", results)
		ctx.IndentedJSON(http.StatusOK, results)
	}
}
