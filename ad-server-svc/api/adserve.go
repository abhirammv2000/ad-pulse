package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type RequestParams struct {
	AdUnitId    string `json:"adunit_id"`
	PublisherId string `json:"publisher_id"`
}

type Native struct {
	Request struct {
		Ver    string `json:"ver"`
		Assets []struct {
			ID       int `json:"id"`
			Required int `json:"required"`
			Img      struct {
				Type int `json:"type"`
				W    int `json:"w"`
				H    int `json:"h"`
			} `json:"img"`
		} `json:"assets"`
	} `json:"request"`
	Ver string `json:"ver"`
}

type Impression struct {
	BidFloorCur string `json:"bidfloorcur"`
	ID          string `json:"id"`
	Native      Native `json:"native"`
}

type RequestBody struct {
	DPL string       `json:"dpl"`
	ID  string       `json:"id"`
	Imp []Impression `json:"imp"`
}

func (server *Server) adserve(ctx *gin.Context) {
	var reqParams RequestParams
	if err := ctx.ShouldBindQuery(&reqParams); err != nil {
		ctx.JSON(http.StatusBadRequest, errResponse(err))
		return
	}

	var reqBody RequestBody
	if err := ctx.ShouldBindJSON(&reqBody); err != nil {
		ctx.JSON(http.StatusBadRequest, errResponse(err))
		return
	}
	adUnitAdress := server.config.AdManagerAddress + "/adunit?" + "adunit_id=" + reqParams.AdUnitId
	publisherAdress := server.config.AdManagerAddress + "/publisher?" + "publisher_id=" + reqParams.PublisherId

	resp, err := http.Get(publisherAdress)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, errResponse(err))
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		ctx.JSON(http.StatusNotFound, errResponse(err))
		return
	}

	resp, err = http.Get(adUnitAdress)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, errResponse(err))
		return
	}
	defer resp.Body.Close()

}
