# Azure Deployment Script for AI Photo Sharing App
# Requirement: Azure CLI installed and logged in (az login)

$RESOURCE_GROUP = "cwaya-ai-prod"
$ACR_NAME = "cwayaacr" # Registry name must be unique globally
$IMAGE_NAME = "ai-photo-sharing"
$APP_NAME = "cwaya-ai-share"
$LOCATION = "centralindia" # Choose your preferred region

Write-Host "--- Starting Azure Deployment Process ---" -ForegroundColor Cyan

# 1. Create Resource Group if not exists
Write-Host "[1/4] Checking Resource Group..." -ForegroundColor Yellow
az group create --name $RESOURCE_GROUP --location $LOCATION

# 2. Create Azure Container Registry if not exists
Write-Host "[2/4] Checking Container Registry (ACR)..." -ForegroundColor Yellow
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic

# 3. Build & Push Image using ACR (Cloud Build)
Write-Host "[3/4] Building image in ACR (Cloud Build)..." -ForegroundColor Yellow
az acr update -n $ACR_NAME --admin-enabled true
az acr build --registry $ACR_NAME --image "${IMAGE_NAME}:latest" --file azure.Dockerfile .

# 4. Create App Service for Containers (if not exists)
Write-Host "[4/4] Configuring Web App for Containers..." -ForegroundColor Yellow
# Create Plan
az appservice plan create --name "cwaya-plan" --resource-group $RESOURCE_GROUP --sku B1 --is-linux

# Create Web App
az webapp create --resource-group $RESOURCE_GROUP --plan "cwaya-plan" --name $APP_NAME --deployment-container-image-name "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest"

# Get ACR Credentials
$ACR_USER = az acr credential show --name $ACR_NAME --query "username" --output tsv
$ACR_PASS = az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv

# Configure Port Mapping and Credentials
Write-Host "Configuring Azure Environment Variables..." -ForegroundColor Yellow
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $APP_NAME --settings WEBSITES_PORT=7860 WEBSITES_CONTAINER_START_TIME_LIMIT=1800 DOCKER_REGISTRY_SERVER_URL="https://${ACR_NAME}.azurecr.io" DOCKER_REGISTRY_SERVER_USERNAME=$ACR_USER DOCKER_REGISTRY_SERVER_PASSWORD=$ACR_PASS

# Set Managed Identity Creds flag (Modern way)
az resource update --ids "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$APP_NAME/config/web" --set properties.acrUseManagedIdentityCreds=True

# Enable System Assigned Identity for ACR pull
az webapp identity assign --resource-group $RESOURCE_GROUP --name $APP_NAME
$id = az webapp identity show --resource-group $RESOURCE_GROUP --name $APP_NAME --query principalId --output tsv
$registryId = az acr show --name $ACR_NAME --query id --output tsv
az role assignment create --assignee $id --scope $registryId --role "AcrPull"

Write-Host "--- Deployment Complete! ---" -ForegroundColor Green
Write-Host "Your app will be available at: https://${APP_NAME}.azurewebsites.net" -ForegroundColor Green
Write-Host "Next Step: Add custom domain ai.cwaya.me in Namecheap and Azure Portal." -ForegroundColor Cyan
