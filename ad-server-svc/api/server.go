package api

import (
	"log"
	"net/http"
	"time"

	"adserver/cache"
	"adserver/util"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

// adManagerTimeout is how long one publisher or ad unit lookup may take. Every
// ad request waits on two of them, so a slow manager has to fail fast.
const adManagerTimeout = 3 * time.Second

// Server answers ad requests over HTTP.
type Server struct {
	config     util.Config
	router     *gin.Engine
	store      cache.Store
	httpClient *http.Client
}

func NewServer(config util.Config, store cache.Store) (*Server, error) {
	server := &Server{
		config:     config,
		store:      store,
		httpClient: &http.Client{Timeout: adManagerTimeout},
	}

	server.setupRouter()
	return server, nil
}

func (server *Server) setupRouter() {
	router := gin.Default()
	config := cors.DefaultConfig()
	config.AllowOrigins = []string{"*"} // open to every origin, restrict this before real use
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

// internalError logs the real error and sends a generic message, so Redis and
// JSON details don't reach callers.
func internalError(ctx *gin.Context, err error) {
	log.Printf("%s %s: %v", ctx.Request.Method, ctx.Request.URL.Path, err)
	ctx.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
}
