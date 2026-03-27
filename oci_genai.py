import oci
import oci_config
import json
import logging
import re

log = logging.getLogger("OCI_GenAI")

# Initialize client
_inference_client = None

# Global token usage tracker
_usage_stats = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

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

def reset_usage():
    """Resets the global token usage counters."""
    global _usage_stats
    _usage_stats = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    log.debug("Global usage stats reset.")

def get_total_usage():
    """Returns the cumulative token usage since last reset."""
    return _usage_stats.copy()

def get_chat_response(prompt: str, system_prompt: str = None, temperature: float = 0.5, max_tokens: int = 2000, include_usage: bool = False):
    """
    Sends a chat request to OCI GenAI.
    Updates global token tracking automatically.
    Returns:
        If include_usage=True: (text, usage_dict)
        Else: text
    """
    global _usage_stats
    client = get_inference_client()
    
    # Construct messages for the chat request
    messages_list = []
    if system_prompt:
        messages_list.append(oci.generative_ai_inference.models.Message(
            role="SYSTEM", 
            content=[oci.generative_ai_inference.models.TextContent(text=system_prompt)]
        ))
    else:
        messages_list.append(oci.generative_ai_inference.models.Message(
            role="SYSTEM", 
            content=[oci.generative_ai_inference.models.TextContent(text="You are a helpful IT support assistant.")]
        ))
    
    messages_list.append(oci.generative_ai_inference.models.Message(
        role="USER", 
        content=[oci.generative_ai_inference.models.TextContent(text=prompt)]
    ))

    chat_request = oci.generative_ai_inference.models.GenericChatRequest(
        messages=messages_list,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=0.9,
    )
    
    chat_details = oci.generative_ai_inference.models.ChatDetails(
        compartment_id=oci_config.COMPARTMENT_ID,
        serving_mode=oci.generative_ai_inference.models.DedicatedServingMode(
            endpoint_id=oci_config.CHAT_MODEL_ID
        ) if ".endpoint" in oci_config.CHAT_MODEL_ID else oci.generative_ai_inference.models.OnDemandServingMode(
            model_id=oci_config.CHAT_MODEL_ID
        ),
        chat_request=chat_request
    )
    
    current_call_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    try:
        response = client.chat(chat_details)
        if not response or not response.data or not response.data.chat_response or not response.data.chat_response.choices:
            err_msg = "Error: Invalid response from GenAI service."
            return (err_msg, current_call_usage) if include_usage else err_msg

        # Extract token usage
        usage_obj = getattr(response.data.chat_response, "usage", None)
        if usage_obj:
            current_call_usage["input_tokens"] = getattr(usage_obj, "prompt_tokens", 0)
            current_call_usage["output_tokens"] = getattr(usage_obj, "completion_tokens", 0)
            current_call_usage["total_tokens"] = getattr(usage_obj, "total_tokens", 0)
        else:
            current_call_usage["input_tokens"] = getattr(response.data.chat_response, 'prompt_token_count', 0)
            current_call_usage["output_tokens"] = getattr(response.data.chat_response, 'completion_token_count', 0)
            current_call_usage["total_tokens"] = current_call_usage["input_tokens"] + current_call_usage["output_tokens"]
        
        # Update global stats
        for k in _usage_stats:
            _usage_stats[k] += current_call_usage.get(k, 0)

        # Logging
        if current_call_usage["total_tokens"] > 0:
            print(f"\nOCI GENAI TOKEN USAGE:-")
            print(f"Input Tokens: {current_call_usage['input_tokens']}")
            print(f"Output Tokens: {current_call_usage['output_tokens']}")
            print(f"Total Tokens: {current_call_usage['total_tokens']}\n")

        result_text = response.data.chat_response.choices[0].message.content[0].text
        if include_usage:
            return result_text, current_call_usage
        return result_text

    except Exception as e:
        log.error(f"Error in GenAI call: {e}")
        if include_usage:
            return f"Error: {e}", current_call_usage
        return f"Error: {e}"
