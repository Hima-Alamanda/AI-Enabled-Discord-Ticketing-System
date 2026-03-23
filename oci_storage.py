import io
import datetime
import oci
import os
from dotenv import load_dotenv

# Load the .env file
load_dotenv()
# Access the variables
NAMESPACE = os.getenv("OCI_NAMESPACE")
BUCKET_NAME = os.getenv("OCI_BUCKET_NAME")
REGION = os.getenv("OCI_REGION")
PAR_EXPIRY_HOURS = 24   # Pre-Authenticated Request link valid for 24 hours

# In-memory cache for PAR URLs (object_name -> {url, expiry_time})
PAR_CACHE = {}


def _get_client() -> oci.object_storage.ObjectStorageClient:
    """Returns an authenticated OCI Object Storage client."""
    config = oci.config.from_file()  # reads ~/.oci/config [DEFAULT]
    return oci.object_storage.ObjectStorageClient(config)



# CORE FUNCTIONS


def upload_file(file_bytes: bytes, object_name: str, content_type: str = "application/octet-stream") -> str:
    """
    Uploads raw bytes to the OCI bucket.

    Args:
        file_bytes   : Raw bytes of the file (use att.getbuffer() for Streamlit uploaders)
        object_name  : Path/name inside the bucket, e.g. 'tickets/TKT-001/0_log.txt'
        content_type : MIME type of the file

    Returns:
        object_name on success, raises exception on failure.
    """
    client = _get_client()
    client.put_object(
        namespace_name=OCI_NAMESPACE,
        bucket_name=OCI_BUCKET_NAME,
        object_name=object_name,
        put_object_body=io.BytesIO(bytes(file_bytes)),
        content_type=content_type
    )
    return object_name


def generate_download_url(object_name: str, expiry_hours: int = PAR_EXPIRY_HOURS) -> str:
    """
    Creates or REUSES an existing Pre-Authenticated Request (PAR) URL.
    This prevents creating thousands of redundant PARs in the OCI console.
    """
    import datetime
    from datetime import timezone
    now = datetime.datetime.now(timezone.utc)
    
    cached = PAR_CACHE.get(object_name)
    if cached:
        cache_expiry = cached['expiry_time']
        # Ensure cache_expiry is aware for comparison
        if cache_expiry.tzinfo is None:
            cache_expiry = cache_expiry.replace(tzinfo=timezone.utc)
            
        # If cache exists and has > 1 hour remaining, reuse it
        if cache_expiry > (now + datetime.timedelta(hours=1)):
            return cached['url']

    client = _get_client()
    
    try:
        existing_pars = client.list_preauthenticated_requests(
            namespace_name=OCI_NAMESPACE,
            bucket_name=OCI_BUCKET_NAME,
            object_name_prefix=object_name
        ).data
        
        for p in existing_pars:
            p_expiry = p.time_expires
            if p_expiry.tzinfo is None:
                p_expiry = p_expiry.replace(tzinfo=timezone.utc)

            if p.object_name == object_name and p_expiry > (now + datetime.timedelta(hours=1)):
                full_url = f"https://objectstorage.{OCI_REGION}.oraclecloud.com{p.access_uri}"
                PAR_CACHE[object_name] = {'url': full_url, 'expiry_time': p_expiry}
                return full_url
    except Exception as e:
        print(f"[oci_storage] Error checking existing PARs: {e}")

    expiry_time = now + datetime.timedelta(hours=expiry_hours)
    
    # Use a clean, stable name
    clean_name = f"par-{object_name.replace('/', '-')}"
    
    par_details = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
        name=clean_name,
        object_name=object_name,
        access_type="ObjectRead",
        time_expires=expiry_time
    )

    response = client.create_preauthenticated_request(
        namespace_name=OCI_NAMESPACE,
        bucket_name=OCI_BUCKET_NAME,
        create_preauthenticated_request_details=par_details
    )

    par_uri = response.data.access_uri
    full_url = f"https://objectstorage.{OCI_REGION}.oraclecloud.com{par_uri}"
    
    # Update cache
    PAR_CACHE[object_name] = {'url': full_url, 'expiry_time': expiry_time}
    
    print(f"[oci_storage] Created new PAR for {object_name} (expires in {expiry_hours}h)")
    return full_url


def list_all_files() -> list[dict]:

    client = _get_client()
    files = []

    try:
        response = client.list_objects(
            namespace_name=OCI_NAMESPACE,
            bucket_name=OCI_BUCKET_NAME,
            fields="name,size,timeModified"
        )

        for obj in response.data.objects:
            name = obj.name
            size_bytes = obj.size or 0
            modified = str(obj.time_modified)[:19] if obj.time_modified else "Unknown"

            # Try to extract ticket ID from naming pattern: tickets/{ticket_id}/...
            parts = name.split("/")
            ticket_id = parts[1] if len(parts) >= 3 else "—"
            display_name = parts[-1]  # just the filename part

            files.append({
                "name": name,
                "display_name": display_name,
                "ticket_id": ticket_id,
                "size_bytes": size_bytes,
                "size_kb": round(size_bytes / 1024, 2),
                "modified": modified
            })

    except oci.exceptions.ServiceError as e:
        print(f"[oci_storage] Error listing bucket objects: {e}")

    return files


def delete_file(object_name: str) -> bool:
    """
    Deletes an object from the bucket.

    Args:
        object_name : The object path inside the bucket

    Returns:
        True on success, False on failure.
    """
    try:
        client = _get_client()
        client.delete_object(
            namespace_name=OCI_NAMESPACE,
            bucket_name=OCI_BUCKET_NAME,
            object_name=object_name
        )
        return True
    except oci.exceptions.ServiceError as e:
        print(f"[oci_storage] Error deleting object '{object_name}': {e}")
        return False


def get_content_type(filename: str) -> str:
    """
    Returns the correct MIME content type based on file extension.
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    mapping = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "pdf": "application/pdf",
        "txt": "text/plain",
        "log": "text/plain",
        "csv": "text/csv",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "md": "text/markdown",
    }
    return mapping.get(ext, "application/octet-stream")
