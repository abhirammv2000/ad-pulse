#!/bin/bash
# Define API endpoints
CAMPAIGNS_API="$AD_MANGER_URL/cache/campaigns"
ADS_API="$AD_MANGER_URL/cache/ads"
CREATIVES_API="$AD_MANGER_URL/cache/creatives"
# Function to call API endpoints
call_api() {
    echo "Calling $1"
    curl -s -X GET "$1" > /dev/null
}
# Call API endpoints
call_api "$CAMPAIGNS_API"
call_api "$ADS_API"
call_api "$CREATIVES_API"