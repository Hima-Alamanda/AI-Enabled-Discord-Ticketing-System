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

def _build_chat_details(model_id: str, messages_list: list, chat_request) -> oci.generative_ai_inference.models.ChatDetails:
    """Builds ChatDetails for a given model ID, handling both dedicated and on-demand serving modes."""
    serving_mode = (
        oci.generative_ai_inference.models.DedicatedServingMode(endpoint_id=model_id)
        if ".endpoint" in model_id
        else oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id)
    )
    return oci.generative_ai_inference.models.ChatDetails(
        compartment_id=oci_config.COMPARTMENT_ID,
        serving_mode=serving_mode,
        chat_request=chat_request
    )


def _extract_response_text(response) -> str:
    """Extracts the text string from an OCI GenAI chat response object."""
    if not response or not response.data or not response.data.chat_response or not response.data.chat_response.choices:
        return ""
    choice = response.data.chat_response.choices[0]
    result_text = ""
    if hasattr(choice, 'message') and choice.message:
        if choice.message.content and len(choice.message.content) > 0:
            result_text = choice.message.content[0].text
    if not result_text and hasattr(choice, 'text'):
        result_text = choice.text
    return result_text


def _extract_usage(response) -> dict:
    """Extracts token usage stats from an OCI GenAI chat response."""
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    if not response or not response.data or not response.data.chat_response:
        return usage
    usage_obj = getattr(response.data.chat_response, "usage", None)
    if usage_obj:
        usage["input_tokens"]  = getattr(usage_obj, "prompt_tokens", 0) or 0
        usage["output_tokens"] = getattr(usage_obj, "completion_tokens", 0) or 0
        usage["total_tokens"]  = getattr(usage_obj, "total_tokens", 0) or 0
    else:
        usage["input_tokens"]  = getattr(response.data.chat_response, 'prompt_token_count', 0) or 0
        usage["output_tokens"] = getattr(response.data.chat_response, 'completion_token_count', 0) or 0
        usage["total_tokens"]  = usage["input_tokens"] + usage["output_tokens"]
    return usage


def get_chat_response(
    prompt: str,
    system_prompt: str = None,
    temperature: float = 0.5,
    max_tokens: int = 2000,
    include_usage: bool = False
):
    """
    Sends a chat request to OCI GenAI with automatic fallback.

    Flow:
        1. Try PRIMARY model (oci_config.CHAT_MODEL_ID).
        2. If it fails for any reason (rate limit, safety filter, timeout, etc.),
           automatically retry with FALLBACK model (oci_config.FALLBACK_MODEL_ID).
        3. If both fail, return a graceful error message.

    Returns:
        If include_usage=True: (text, usage_dict)
        Else: text
    """
    global _usage_stats
    client = get_inference_client()

    # --- Build shared message list (same for both primary & fallback) ---
    messages_list = []
    messages_list.append(oci.generative_ai_inference.models.Message(
        role="SYSTEM",
        content=[oci.generative_ai_inference.models.TextContent(
            text=system_prompt if system_prompt else "You are a helpful IT support assistant."
        )]
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

    current_call_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    #  Model cascade: primary → fallback 
    models_to_try = [
        (oci_config.CHAT_MODEL_ID,     "PRIMARY"),
        (oci_config.FALLBACK_MODEL_ID, "FALLBACK"),
    ]

    last_error = None
    for model_id, model_label in models_to_try:
        log.info(f"[GenAI] Attempting {model_label} model: {model_id}")
        try:
            chat_details = _build_chat_details(model_id, messages_list, chat_request)
            response = client.chat(chat_details)

            result_text = _extract_response_text(response)
            if not result_text:
                raise ValueError("Model returned an empty or filtered response.")

            current_call_usage = _extract_usage(response)

            # Update global cumulative stats
            for k in _usage_stats:
                _usage_stats[k] += current_call_usage.get(k, 0)

            # Token usage log
            if current_call_usage["total_tokens"] > 0:
                print(f"\nOCI GENAI TOKEN USAGE [{model_label} — {model_id}]:")
                print(f"  Input Tokens:  {current_call_usage['input_tokens']}")
                print(f"  Output Tokens: {current_call_usage['output_tokens']}")
                print(f"  Total Tokens:  {current_call_usage['total_tokens']}\n")

            if model_label == "FALLBACK":
                log.warning(
                    f"[GenAI] PRIMARY model failed. Response served by FALLBACK model: {model_id}. "
                    f"Primary error was: {last_error}"
                )

            if include_usage:
                return result_text, current_call_usage
            return result_text

        except Exception as e:
            last_error = e
            log.error(f"[GenAI] {model_label} model ({model_id}) failed: {e}")
            if model_label == "PRIMARY":
                log.warning(f"[GenAI] Switching to FALLBACK model ({oci_config.FALLBACK_MODEL_ID})...")
            # Loop continues to next model in cascade

    # --- Both models failed ---
    err_msg = (
        f"I'm sorry, I'm currently experiencing connectivity issues with the AI service. "
        f"Please try again in a few moments. (Error: {last_error})"
    )
    log.error(f"[GenAI] ALL models failed. Last error: {last_error}")
    if include_usage:
        return err_msg, current_call_usage
    return err_msg
