import os
import uuid
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceNotFoundError
import logging

class AzureBlobService:
    def __init__(self):
        self.connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        self.account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        self.account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
        self.container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'food-scanner-images')
        
        # For local testing, we can use a mock service
        self.is_local = not self.connection_string and not (self.account_name and self.account_key)
        
        if not self.is_local:
            if self.connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            elif self.account_name and self.account_key:
                self.blob_service_client = BlobServiceClient(
                    account_url=f"https://{self.account_name}.blob.core.windows.net",
                    credential=self.account_key
                )
            else:
                raise ValueError("Azure Storage credentials not found. Set AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY")
            
            # Ensure container exists
            self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Ensure the blob container exists, create if it doesn't."""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.get_container_properties()
        except ResourceNotFoundError:
            container_client = self.blob_service_client.create_container(self.container_name)
            logging.info(f"Created container: {self.container_name}")
    
    def upload_image(self, image_data, user_email, original_filename=None):
        """
        Upload an image to Azure Blob Storage.
        
        Args:
            image_data: Bytes of the image
            user_email: Email of the user uploading the image
            original_filename: Original filename (optional)
            
        Returns:
            dict: Contains 'url', 'blob_name', and 'local_path' (for local testing)
        """
        if self.is_local:
            return self._upload_local(image_data, user_email, original_filename)
        
        # Generate unique blob name with email and date organization
        timestamp = datetime.utcnow()
        date_folder = timestamp.strftime('%Y-%m-%d')
        time_str = timestamp.strftime('%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        file_extension = self._get_file_extension(original_filename) if original_filename else '.jpg'
        
        # Create blob name with email and date organization
        # Format: email/YYYY-MM-DD/HHMMSS_uniqueid.extension
        blob_name = f"{user_email}/{date_folder}/{time_str}_{unique_id}{file_extension}"
        
        try:
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            # Upload the image
            blob_client.upload_blob(image_data, overwrite=True)
            
            # Store only the blob name, generate SAS token on-demand when needed
            return {
                'url': None,  # Will be generated on-demand
                'blob_name': blob_name,
                'local_path': None
            }
            
        except Exception as e:
            logging.error(f"Error uploading to Azure Blob: {str(e)}")
            raise
    
    def _upload_local(self, image_data, user_email, original_filename=None):
        """
        For local testing, save images to a local directory.
        """
        import tempfile
        import os
        
        # Create local storage directory
        local_storage_dir = os.path.join(os.path.dirname(__file__), '..', 'local_storage', 'images')
        os.makedirs(local_storage_dir, exist_ok=True)
        
        # Create user directory with email (sanitized for filesystem)
        safe_email = user_email.replace('@', '_at_').replace('.', '_')
        user_dir = os.path.join(local_storage_dir, safe_email)
        os.makedirs(user_dir, exist_ok=True)
        
        # Create date folder
        timestamp = datetime.utcnow()
        date_folder = timestamp.strftime('%Y-%m-%d')
        date_dir = os.path.join(user_dir, date_folder)
        os.makedirs(date_dir, exist_ok=True)
        
        # Generate filename
        time_str = timestamp.strftime('%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        file_extension = self._get_file_extension(original_filename) if original_filename else '.jpg'
        filename = f"{time_str}_{unique_id}{file_extension}"
        
        # Save file locally
        file_path = os.path.join(date_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Return local file URL (for development)
        relative_path = os.path.relpath(file_path, os.path.join(os.path.dirname(__file__), '..'))
        local_url = f"/local_storage/images/{safe_email}/{date_folder}/{filename}"
        
        return {
            'url': local_url,
            'blob_name': f"{user_email}/{date_folder}/{filename}",
            'local_path': file_path
        }
    
    def _get_file_extension(self, filename):
        """Extract file extension from filename."""
        if not filename:
            return '.jpg'
        return os.path.splitext(filename)[1] or '.jpg'
    
    def _generate_sas_token(self, blob_name, expiry_hours=24):
        """Generate SAS token for secure access to private blobs."""
        try:
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                account_key=self.account_key,
                container_name=self.container_name,
                blob_name=blob_name,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )
            return sas_token
        except Exception as e:
            logging.warning(f"Could not generate SAS token: {str(e)}")
            return None
    
    def delete_image(self, blob_name):
        """Delete an image from Azure Blob Storage."""
        if self.is_local:
            return self._delete_local(blob_name)
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            blob_client.delete_blob()
            return True
        except Exception as e:
            logging.error(f"Error deleting blob: {str(e)}")
            return False
    
    def _delete_local(self, blob_name):
        """Delete local file for testing."""
        try:
            local_storage_dir = os.path.join(os.path.dirname(__file__), '..', 'local_storage', 'images')
            file_path = os.path.join(local_storage_dir, blob_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            logging.error(f"Error deleting local file: {str(e)}")
        return False
    
    def get_image_url(self, blob_name, expiry_hours=720):  # 30 days default
        """Get the URL for an image with fresh SAS token."""
        if self.is_local:
            return f"/local_storage/images/{blob_name}"
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            # Generate fresh SAS token on-demand
            sas_token = self._generate_sas_token(blob_name, expiry_hours)
            
            if sas_token:
                return f"{blob_client.url}?{sas_token}"
            else:
                # Fallback to direct URL if SAS generation fails
                return blob_client.url
                
        except Exception as e:
            logging.error(f"Error getting blob URL: {str(e)}")
            return None 