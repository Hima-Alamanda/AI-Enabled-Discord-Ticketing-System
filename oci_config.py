import oci
import os
import os
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

#OCI CONFIGURATION 
COMPARTMENT_ID = os.getenv("COMPARTMENT_ID")
REGION = os.getenv("OCI_REGION")

# OCI Generative AI Service Endpoints
GENAI_INFERENCE_ENDPOINT = f"https://inference.generativeai.{REGION}.oci.oraclecloud.com"


#using Gemini 2.5 Flash ( google.gemini-2.5-pro ), ( xai.grok-4.20-reasoning )
CHAT_MODEL_ID = "xai.grok-4.20-reasoning"
#CHAT_MODEL_ID = "google.gemini-2.5-pro"



# OCI SETTINGS (From oci_storage.py) 
NAMESPACE = os.getenv("OCI_NAMESPACE")
BUCKET_NAME = os.getenv("OCI_BUCKET_NAME")

def get_config():
    try:
        return oci.config.from_file()
    except Exception as e:
        print(f"Error loading OCI config: {e}")
        return None
