import oci
import os

#OCI CONFIGURATION 
COMPARTMENT_ID = "ocid1.compartment.oc1..aaaaaaaayvwmx7qejmczmtqzgos7nonbycbkyonxleqiljo76zywbmw53vlq"
REGION = "us-ashburn-1"

# OCI Generative AI Service Endpoints
GENAI_INFERENCE_ENDPOINT = f"https://inference.generativeai.{REGION}.oci.oraclecloud.com"


# We are using Gemini 2.5 Flash 
CHAT_MODEL_ID = "google.gemini-2.5-flash"

# OTHER OCI SETTINGS (From oci_storage.py) 
OCI_NAMESPACE   = "id1h3njyvxzi"
OCI_BUCKET_NAME = "ticketing-attachments"

def get_config():
    """Returns the OCI config from ~/.oci/config."""
    try:
        return oci.config.from_file()
    except Exception as e:
        print(f"Error loading OCI config: {e}")
        return None
