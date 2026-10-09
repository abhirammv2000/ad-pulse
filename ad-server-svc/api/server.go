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

// How many decoded values each generation of the parse caches holds. An ad is about 1 KB of JSON, so the ad cache
// should stay near 30 MB at twice this limit (an estimate from the size of an ad, not measured), and the campaign list changes rarely.
const (
	decodedAdLimit           = 8192
	decodedCampaignListLimit = 8
)

// Server answers ad requests over HTTP.
type Server struct {
	config     util.Config
	router     *gin.Engine
	store      cache.Store
	httpClient *http.Client
	known      *knownEntities

	// Decoded campaigns and ads, kept by their JSON text. See contentCache.
	campaignsDecoded *contentCache[[]cache.Campaign]
	adsDecoded       *contentCache[cache.Ad]
}

func NewServer(config util.Config, store cache.Store) (*Server, error) {
	server := &Server{
		config:     config,
		store:      store,
		httpClient: &http.Client{Timeout: adManagerTimeout},
		known:      newKnownEntities(),

		campaignsDecoded: newContentCache[[]cache.Campaign](decodedCampaignListLimit),
		adsDecoded:       newContentCache[cache.Ad](decodedAdLimit),
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
