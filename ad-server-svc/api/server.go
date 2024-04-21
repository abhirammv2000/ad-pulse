package api

import (
	"adserver/cache"
	"adserver/util"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

// serve HTTP requests for banking service.
type Server struct {
	config util.Config
	router *gin.Engine
	store  cache.Store
}

func NewServer(config util.Config, store cache.Store) (*Server, error) {
	server := &Server{
		config: config,
		store:  store,
	}

	server.setupRouter()
	return server, nil
}

func (server *Server) setupRouter() {
	router := gin.Default()
	config := cors.DefaultConfig()
	config.AllowOrigins = []string{"*"} // Change this to your allowed origins
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE"}
	router.Use(cors.New(config))
	router.GET("/", server.healthCheck)
	router.POST("/adserve", server.adserve)

	server.router = router
}

func (server *Server) Start(address string) error {
	return server.router.Run(address)
}

func errResponse(err error) gin.H {
	return gin.H{"error": err.Error()}
}
