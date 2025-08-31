# Deploy Docker Container to Azure App Service

## Option 1: Use Azure App Service with Docker (Recommended)

Since you already have an Azure App Service, you can configure it to use your Docker container instead of the built-in Python runtime.

### Steps:

1. **In Azure Portal, go to your App Service (food-app)**

2. **Configure Docker:**

   - Go to **Settings** → **General settings**
   - Change **Stack** from "Python" to "Docker"
   - Set **Image source** to "Docker Hub" or "Azure Container Registry"

3. **If using Docker Hub:**

   - Push your image to Docker Hub first:

   ```bash
   docker tag food-app:latest your-dockerhub-username/food-app:latest
   docker push your-dockerhub-username/food-app:latest
   ```

   - Set **Image and tag** to: `your-dockerhub-username/food-app:latest`

4. **If using Azure Container Registry:**

   - Create an ACR and push your image there
   - Set **Image and tag** to: `your-registry.azurecr.io/food-app:latest`

5. **Set Environment Variables:**

   - Go to **Settings** → **Configuration** → **Application settings**
   - Add all your environment variables (DATABASE_URL, etc.)

6. **Deploy:**
   - Save the configuration
   - The App Service will automatically pull and run your Docker container

## Option 2: Azure Container Instances

Use the `deploy_to_azure.sh` script after setting up Azure Container Registry.

## Benefits of Docker Approach:

- ✅ **No more startup script issues**
- ✅ **Consistent environment** (local = production)
- ✅ **Easy debugging** (test exact same container locally)
- ✅ **Better resource utilization**
- ✅ **More portable** (can run on any cloud)

## Next Steps:

1. Choose your preferred deployment method
2. Update the environment variables with your actual values
3. Deploy and test!
