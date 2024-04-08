package services

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/nedpals/supabase-go"
)

func CSCServiceHandler(supabaseClient *supabase.Client) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var results map[string]interface{}
		err := supabaseClient.DB.From("ads").Select("*").Single().Execute(&results)
		if err != nil {
			ctx.IndentedJSON(http.StatusInternalServerError, gin.H{
				"status":  "error",
				"message": err.Error(),
			})
			return
		}
		ctx.IndentedJSON(http.StatusOK, results)
	}
}
