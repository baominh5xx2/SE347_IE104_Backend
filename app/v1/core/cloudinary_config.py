"""
Cloudinary Configuration
"""
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Optional, List, Dict, Any
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class CloudinaryConfig:
    """Cloudinary configuration and helper functions"""
    
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize Cloudinary configuration from environment variables"""
        if cls._initialized:
            return
        
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        
        if not all([cloud_name, api_key, api_secret]):
            logger.warning("Cloudinary credentials not found in environment variables")
            return
        
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        
        cls._initialized = True
        logger.info("Cloudinary initialized successfully")
    
    @staticmethod
    def upload_image(
        file_content: bytes,
        filename: str,
        folder: str = "tour_packages"
    ) -> Optional[Dict[str, Any]]:
        """
        Upload image to Cloudinary
        
        Args:
            file_content: Binary content of the image
            filename: Original filename
            folder: Cloudinary folder to store image
            
        Returns:
            Dict containing upload result with 'url' and 'public_id'
        """
        try:
            CloudinaryConfig.initialize()
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file_content,
                folder=folder,
                resource_type="image",
                public_id=filename.split('.')[0],  # Use filename without extension
                overwrite=True,
                invalidate=True
            )
            
            return {
                "url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format")
            }
            
        except Exception as e:
            logger.error(f"Error uploading image to Cloudinary: {str(e)}")
            return None
    
    @staticmethod
    def upload_multiple_images(
        files: List[tuple],  # List of (file_content, filename)
        folder: str = "tour_packages"
    ) -> List[str]:
        """
        Upload multiple images to Cloudinary in parallel using ThreadPoolExecutor
        
        Args:
            files: List of tuples containing (file_content, filename)
            folder: Cloudinary folder to store images
            
        Returns:
            List of image URLs (in the same order as input files)
        """
        def upload_single(file_data):
            """Helper function to upload a single image"""
            file_content, filename = file_data
            result = CloudinaryConfig.upload_image(file_content, filename, folder)
            if result and result.get("url"):
                return result["url"]
            return None
        
        # Use ThreadPoolExecutor to upload images in parallel
        # Max workers = min(10, number of files) for optimal performance
        max_workers = min(10, len(files))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all upload tasks and maintain order
            results = list(executor.map(upload_single, files))
        
        # Filter out None values (failed uploads)
        urls = [url for url in results if url is not None]
        
        return urls
    
    @staticmethod
    def delete_image(public_id: str) -> bool:
        """
        Delete image from Cloudinary
        
        Args:
            public_id: Cloudinary public_id of the image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            CloudinaryConfig.initialize()
            
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
            
        except Exception as e:
            logger.error(f"Error deleting image from Cloudinary: {str(e)}")
            return False
    
    @staticmethod
    def delete_multiple_images(public_ids: List[str]) -> int:
        """
        Delete multiple images from Cloudinary in parallel using ThreadPoolExecutor
        
        Args:
            public_ids: List of Cloudinary public_ids
            
        Returns:
            Number of successfully deleted images
        """
        if not public_ids:
            return 0
        
        # Use ThreadPoolExecutor to delete images in parallel
        max_workers = min(10, len(public_ids))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all delete tasks
            results = list(executor.map(CloudinaryConfig.delete_image, public_ids))
        
        # Count successful deletions
        deleted_count = sum(1 for success in results if success)
        
        return deleted_count
    
    @staticmethod
    def extract_public_id_from_url(url: str) -> Optional[str]:
        """
        Extract public_id from Cloudinary URL
        
        Args:
            url: Cloudinary image URL
            
        Returns:
            Public ID or None
        """
        try:
            # URL format: https://res.cloudinary.com/{cloud_name}/image/upload/v{version}/{folder}/{public_id}.{format}
            if "cloudinary.com" in url:
                parts = url.split("/upload/")
                if len(parts) == 2:
                    # Get the part after /upload/
                    path = parts[1]
                    # Remove version (v1234567890/)
                    if path.startswith("v"):
                        path = "/".join(path.split("/")[1:])
                    # Remove file extension
                    public_id = ".".join(path.split(".")[:-1])
                    return public_id
            return None
        except Exception as e:
            logger.error(f"Error extracting public_id from URL: {str(e)}")
            return None


# Initialize on module import
CloudinaryConfig.initialize()
