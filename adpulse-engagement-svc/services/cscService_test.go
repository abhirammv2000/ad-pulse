package services

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/nedpals/supabase-go"
)

func TestCSCServiceHandler(t *testing.T) {
	// Create a new Supabase client for testing
	supabaseClient := supabase.CreateClient("test-url", "test-key")

	// Create a new Gin router
	router := gin.Default()

	// Set up the route with the CSCServiceHandler function
	router.GET("/csc", CSCServiceHandler(supabaseClient))

	// Create a new HTTP request for testing
	req, err := http.NewRequest("GET", "/csc", nil)
	if err != nil {
		t.Fatal(err)
	}

	// Create a new HTTP response recorder
	recorder := httptest.NewRecorder()
	recorder.Header().Set("Test-Header", "expectedHeader")
	jsonString := `[
		{
			"advertiserid": "A12345",
			"advertisername": "Nike",
			"advertiserstate": "ACTIVE",
			"advertisertype": "PAID",
			"brands": null,
			"contactinfo": {
				"primaryContact": "nike@nike.com",
				"primaryName": "Nike"
			},
			"createdat": "2024-03-17T12:39:56",
			"createdby": "kushal.1nagaraj.1@gmail.com",
			"industry": "Sports",
			"updatedat": "2024-03-17T12:39:56",
			"updatedby": "kushal.1nagaraj.1@gmail.com"
		}
	]`

	recorder.Body.Write([]byte(jsonString))

	router.ServeHTTP(recorder, req)

	// Check the response status code
	if recorder.Code != http.StatusOK {
		t.Errorf("Expected status code %d, but got %d", http.StatusOK, recorder.Code)
	}

	if req.URL.Path != "/csc" {
		t.Errorf("Expected request URL path /csc, but got %q", req.URL.Path)
	}

	if req.Body != nil {
		t.Errorf("Expected request body to be nil, but got %v", req.Body)
	}

	expectedStatusCode := http.StatusOK
	if recorder.Code != expectedStatusCode {
		t.Errorf("Expected response status code %d, but got %d", expectedStatusCode, recorder.Code)
	}

	expectedHeader := "Test-Header"
	if recorder.Header().Get("Test-Header") != "expectedHeader" {
		t.Errorf("Expected response header %q, but got %q", expectedHeader, recorder.Header().Get("Test-Header"))
	}

	if recorder.Body.Len() == 0 {
		t.Errorf("Expected non-empty response body, but got an empty body")
	}
}