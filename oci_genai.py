import oci
import oci_config
import json

# Initialize clients
_inference_client = None

def get_inference_client():
    global _inference_client
    if _inference_client is None:
        config = oci_config.get_config()
        _inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
            config, 
            service_endpoint=oci_config.GENAI_INFERENCE_ENDPOINT,
            retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
        )
    return _inference_client

def get_chat_response(prompt, system_prompt=None, temperature=0.2, max_tokens=2000):
    """
    Generates a chat response using OCI Generative AI (Gemini).
    """
    client = get_inference_client()
    
    # Construct Messages using the correct OCI SDK classes
    messages = []
    if system_prompt:
        # SystemMessage class from oci.generative_ai_inference.models
        system_msg = oci.generative_ai_inference.models.SystemMessage()
        system_msg.content = [oci.generative_ai_inference.models.TextContent(text=system_prompt)]
        messages.append(system_msg)
    
    # UserMessage class from oci.generative_ai_inference.models
    user_msg = oci.generative_ai_inference.models.UserMessage()
    user_msg.content = [oci.generative_ai_inference.models.TextContent(text=prompt)]
    messages.append(user_msg)
    
    chat_details = oci.generative_ai_inference.models.ChatDetails()
    chat_details.compartment_id = oci_config.COMPARTMENT_ID
    chat_details.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id=oci_config.CHAT_MODEL_ID)
    
    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.messages = messages
    chat_request.max_tokens = max_tokens
    chat_request.temperature = temperature
    
    chat_details.chat_request = chat_request
    
    print(f"[OCI] Using Compartment: {oci_config.COMPARTMENT_ID[:20]}...")
    print(f"[OCI] Using Model: {oci_config.CHAT_MODEL_ID}")
    print(f"[OCI] Endpoint: {oci_config.GENAI_INFERENCE_ENDPOINT}")
    
    print("PROMPT DEBUG:-")
    print(f"Prompt length (characters): {len(prompt)}")
    print(" ")

    try:
        response = client.chat(chat_details)
        if not response or not response.data:
            print("[OCI] Empty response received from GenAI service.")
            return "Error: No data in OCI response."

        # Log Token Usage Metadata
        usage = getattr(response.data.chat_response, "usage", None)
        if usage:
            input_tokens = getattr(usage, "prompt_tokens", "unknown")
            output_tokens = getattr(usage, "completion_tokens", "unknown")
            total_tokens = getattr(usage, "total_tokens", "unknown")

            print("OCI GENAI TOKEN USAGE:-")
            print(f"Input Tokens: {input_tokens}")
            print(f"Output Tokens: {output_tokens}")
            print(f"Total Tokens: {total_tokens}")
            print(" ")

        chat_resp = response.data.chat_response
        if not chat_resp or not chat_resp.choices:
            print(f"[OCI] No choices in response. Resp: {chat_resp}")
            return "Error: AI returned no choices."

        choice = chat_resp.choices[0]
        if not choice or not hasattr(choice, 'message') or not choice.message:
             print(f"[OCI] Choice message is None. Finish Reason: {getattr(choice, 'finish_reason', 'Unknown')}")
             return f"Error: AI response blocked or empty (Reason: {getattr(choice, 'finish_reason', 'N/A')})"

        if not hasattr(choice.message, 'content') or not choice.message.content or len(choice.message.content) == 0:
             print(f"[OCI] Choice message content is empty/None")
             return "Error: AI response contained no text content."

        # Extract response text safely
        text = choice.message.content[0].text
        
        return text
    except Exception as e:
        print(f"Error getting OCI chat response: {e}")
        # Print more details about the error if possible
        if hasattr(e, 'status'):
            print(f"Status: {e.status}, Message: {e.message}")
        return f"OCI GenAI Error: {str(e)}"

if __name__ == "__main__":
    import oci_config
    print(f"Testing OCI with model: {oci_config.CHAT_MODEL_ID}")
    print("Testing OCI with system prompt...")
    resp = get_chat_response("Hi there!", system_prompt="You are a helpful assistant.")
    print(f"Response: {resp}")
