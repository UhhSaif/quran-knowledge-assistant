#!/bin/bash

# Deployment script for Google Cloud Run

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Quran Assistant Cloud Run Deployment ===${NC}\n"

# Check required environment variables
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT is not set${NC}"
    exit 1
fi

if [ -z "$TAVILY_API_KEY" ]; then
    echo -e "${YELLOW}Warning: TAVILY_API_KEY is not set${NC}"
fi

# Configuration
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
REGION=${GOOGLE_CLOUD_LOCATION:-us-central1}
SERVICE_NAME="quran-assistant"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo -e "${GREEN}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo ""

# Build the container image
echo -e "${GREEN}Step 1: Building container image...${NC}"
docker build -t $IMAGE_NAME:latest .

# Push to Google Container Registry
echo -e "${GREEN}Step 2: Pushing image to GCR...${NC}"
docker push $IMAGE_NAME:latest

# Create secret for Tavily API key if it doesn't exist
echo -e "${GREEN}Step 3: Setting up secrets...${NC}"
if ! gcloud secrets describe TAVILY_API_KEY --project=$PROJECT_ID &> /dev/null; then
    echo "Creating TAVILY_API_KEY secret..."
    echo -n "$TAVILY_API_KEY" | gcloud secrets create TAVILY_API_KEY \
        --data-file=- \
        --project=$PROJECT_ID
else
    echo "TAVILY_API_KEY secret already exists"
fi

# Deploy to Cloud Run
echo -e "${GREEN}Step 4: Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME:latest \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,GOOGLE_GENAI_USE_VERTEXAI=true" \
    --set-secrets "TAVILY_API_KEY=TAVILY_API_KEY:latest" \
    --project $PROJECT_ID

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --project $PROJECT_ID \
    --format 'value(status.url)')

echo ""
echo -e "${GREEN}=== Deployment Complete! ===${NC}"
echo -e "${GREEN}Service URL: ${YELLOW}$SERVICE_URL${NC}"
echo ""
echo "Test the service:"
echo "  Health check: curl $SERVICE_URL/health"
echo "  Chat: curl -X POST $SERVICE_URL/chat -H 'Content-Type: application/json' -d '{\"message\": \"What does the Quran say about patience?\"}'"
echo ""
