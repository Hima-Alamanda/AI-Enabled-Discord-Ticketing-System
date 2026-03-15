import re
import requests
import json
import utils
import oci_genai

def analyze_ticket_with_ai(text):
    """
    Combined AI call to predict ticket fields AND extract tags in one go using OCI GenAI (Cloud).
    Superior to local LLMs in reasoning and tag extraction.
    """
    if not text or len(text.strip()) < 10:
        return {
            "fields": {
                "instance": "PROD - Production",
                "deployment": "On-Premise",
                "type": "Incident",
                "topic": "IT Infrastructure & Hardware",
                "severity": "Medium",
                "company": "Internal"
            },
            "tags": []
        }

    # Determine the "Tag Budget" based on text length
    text_length = len(text)
    # If there are attachments (indicated by [CONTENT FROM]), increase the budget
    has_attachments = "[CONTENT FROM" in text
    
    if has_attachments or text_length > 300:
        tag_instruction = "Extract the 5 to 8 MOST IMPORTANT and SPECIFIC tags. Do not exceed 10."
    else:
        tag_instruction = "Extract the 3 to 5 MOST IMPORTANT tags. Do not exceed 6."

    # Combined System Prompt for Fields + Tags
    system_prompt = f"""You are an Expert IT Support AI specializing in ticket categorization and semantic tag extraction.
    
    **ATTACHMENT ANALYSIS (CRITICAL)**: 
    - You will see text blocks marked as `[CONTENT FROM filename.ext]`. These are extracted from attachments.
    - **MANDATORY**: You MUST scan these attachment blocks for specific technical details.
    - Extract tags for: specific error codes (e.g., ORA-12154, 404, 500, ERR_CONNECTION_REFUSED), software names (JDE, SAP, Oracle, VPN Client), and hardware models.
    
    **Your Task**:
    1. Extract semantic tags that represent the core issues, technologies, and entities mentioned.
    2. Categorize the ticket into the provided valid field options.
    
    **Tag Extraction Guidelines**:
    - {tag_instruction}
    - BE SPECIFIC: Prefer "VPN Connectivity" over "Network".
    - PRIORITIZE: Technical entities and error codes found in attachments.
    
    **Valid Field Options**:
    - Instance: ["DEV - Development", "QA / TEST - Testing", "UAT - User Acceptance Testing", "PROD - Production", "Other (Custom...)"]
    - Deployment: ["On-Premise", "Cloud", "Other (Custom...)"]
    - Type: ["Incident", "Service Request", "Problem", "Change Request", "Other (Custom...)"]
    - Topic: ["Finance", "HR", "Supply Chain", "Manufacturing", "Sales", "IT Infrastructure & Hardware", "Access & Identity", "Other (Custom...)"]
    - Severity: ["Low", "Medium", "High", "Critical"]
    - Company: ["CNG", "GLESBY", "Sensanate", "PCB", "NoblQ", "Internal", "Other (Custom...)"]

    **IMPORTANT**: Output ONLY valid JSON in the exact format shown below. Put "tags" FIRST to ensure they are captured.
    Format:
    {{
      "tags": ["tag1", "tag2", ...],
      "fields": {{
        "instance": "...",
        "deployment": "...",
        "type": "...",
        "topic": "...",
        "severity": "...",
        "company": "..."
      }}
    }}
    """
    
    try:
        # Using OCI GenAI (Cloud) - max_tokens to 2000
        response_text = oci_genai.get_chat_response(
            prompt=f"Analyze this ticket and extract details and tags (tags first!):\n\nTicket Data:\n{text}\n\nJSON:",
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=2000
        )
        
        print(f"AI Response Text: {response_text}")
        
        # Robust JSON cleaning
        if response_text:
            try:
                # Remove markdown code blocks if present
                clean_json = response_text
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                
                # Further clean if it's still containing braces
                if "{" in clean_json:
                    start = clean_json.find("{")
                    # If it's truncated, it might not have an end brace
                    if "}" in clean_json:
                        end = clean_json.rfind("}") + 1
                        clean_json_str = clean_json[start:end]
                    else:
                        clean_json_str = clean_json[start:]
                else:
                    clean_json_str = clean_json
                
                # Pre-clean: Remove trailing commas
                clean_json_str = re.sub(r',\s*\]', ']', clean_json_str)
                clean_json_str = re.sub(r',\s*\}', '}', clean_json_str)
                
                raw_data = {}
                try:
                    # If it's truncated (no closing brace), this will fail
                    raw_data = json.loads(clean_json_str)
                except json.JSONDecodeError:
                    print("DEBUG: JSON decode failed, attempting fallback regex extraction...")
                    # Look for "tags": [ "item1", "item2" ...
                    tag_match = re.search(r'"tags":\s*\[(.*?)\]', response_text, re.IGNORECASE | re.DOTALL)
                    if not tag_match:
                        # Even if the array isn't closed, try to grab what we can
                        tag_match = re.search(r'"tags":\s*\[(.*)', response_text, re.IGNORECASE | re.DOTALL)
                    
                    if tag_match:
                        tags_str = tag_match.group(1)
                        # Extract strings between quotes
                        raw_data["tags"] = re.findall(r'"([^"]*)"', tags_str)
                    
                    for field in ['instance', 'deployment', 'type', 'topic', 'severity', 'company']:
                        f_match = re.search(f'"{field}":\\s*"([^"]*)"', response_text, re.IGNORECASE)
                        if f_match:
                            raw_data[field] = f_match.group(1)

                # Normalize keys to lowercase
                data = {k.lower(): v for k, v in raw_data.items()}
                
                # Check for nested "fields" object
                fields_data = data.get("fields")
                if not fields_data or not isinstance(fields_data, dict):
                    fields_data = data

                # Helper to ensure simple string values
                def clean_field(val, default_fn, text):
                    if isinstance(val, list) and len(val) > 0:
                        val = val[0]
                    if val is None or str(val).strip().lower() in ["none", "null", ""] :
                        return default_fn(text)
                    return str(val).strip()

                # Robust Tag Extraction
                tags = []
                
                if "tags" in data:
                    val = data["tags"]
                    if isinstance(val, list):
                        tags.extend(val)
                    elif isinstance(val, str):
                        tags.extend([t.strip() for t in val.split(",") if t.strip()])
                
                if not tags and "all_tags" in data:
                    val = data["all_tags"]
                    if isinstance(val, list):
                        tags.extend(val)
                    elif isinstance(val, str):
                        tags.extend([t.strip() for t in val.split(",") if t.strip()])
                
                # Filter and clean
                final_tags = []
                seen_lower = set()
                for t in tags:
                    t_str = str(t).strip()
                    if t_str and len(t_str) > 1:
                        # Remove quotes if AI included them in a string list
                        t_str = t_str.strip('"').strip("'")
                        t_lower = t_str.lower()
                        if t_lower not in seen_lower:
                            final_tags.append(t_str)
                            seen_lower.add(t_lower)

                print(f"DEBUG: Extracted Tags: {final_tags}")

                return {
                    "fields": {
                        "instance": clean_field(fields_data.get("instance"), predict_instance, text),
                        "deployment": clean_field(fields_data.get("deployment"), predict_deployment, text),
                        "type": clean_field(fields_data.get("type"), predict_ticket_type, text),
                        "topic": clean_field(fields_data.get("topic"), predict_topic, text),
                        "severity": clean_field(fields_data.get("severity"), predict_severity, text),
                        "company": clean_field(fields_data.get("company"), lambda x: "Internal", text)
                    },
                    "tags": final_tags[:10],
                    "raw_json_debug": response_text
                }
            except Exception as json_e:
                print(f"DEBUG: AI Analysis Logic Error: {json_e}")
                return {
                    "fields": {
                        "instance": predict_instance(text),
                        "deployment": predict_deployment(text),
                        "type": predict_ticket_type(text),
                        "topic": predict_topic(text),
                        "severity": predict_severity(text),
                        "company": "Internal"
                    },
                    "tags": [],
                    "raw_json_debug": f"Parsing Error: {str(json_e)} | Raw: {response_text[:200]}"
                }
    except Exception as e:
        print(f"OCI AI Analysis Failed: {e}")
    
    # Simple Fallback if AI fails completely (using the basic field predictors)
    return {
        "fields": {
            "instance": predict_instance(text),
            "deployment": predict_deployment(text),
            "type": predict_ticket_type(text),
            "topic": predict_topic(text),
            "severity": predict_severity(text),
            "company": "Internal"
        },
        "tags": [] # No tags if AI fails 
    }


def predict_topic(text):
    if not text: return "Other (Custom...)"
    text = text.lower()
    topic_keywords = {
        "Finance": ["invoice", "payment", "cost", "charge", "bill", "finance", "accounting", "ledger"],
        "HR": ["payroll", "salary", "leave", "hiring", "employee", "onboarding", "hr"],
        "Supply Chain": ["supplier", "logistics", "shipping", "inventory", "stock", "warehouse", "scm"],
        "Manufacturing": ["production", "factory", "plant", "machine", "assembly", "mfg"],
        "Sales": ["quote", "order", "crm", "customer", "lead", "opportunity", "sales"],
        "IT Infrastructure & Hardware": ["laptop", "wifi", "network", "server", "vpn", "internet", "printer", "device", "slow"],
        "Access & Identity": ["login", "password", "access", "permission", "locked", "account", "mfa", "2fa", "cant login"],
    }
    for topic, words in topic_keywords.items():
        if any(word in text for word in words):
            return topic
    return "Other (Custom...)"

def predict_severity(text):
    if not text: return "Low"
    text = text.lower()
    critical_keywords = ["urgent", "immediately", "asap", "blocked", "critical", "outage", "system down", "fail"]
    high_keywords = ["important", "deadline", "error", "unable", "broken"]
    if any(word in text for word in critical_keywords):
        return "Critical"
    elif any(word in text for word in high_keywords):
        return "High"
    return "Low"

def predict_instance(text):
    if not text: return "DEV - Development"
    text = text.lower()
    if any(k in text for k in ["prod", "live", "production", "real"]):
        return "PROD - Production"
    if any(k in text for k in ["uat", "acceptance", "user test"]):
        return "UAT - User Acceptance Testing"
    if any(k in text for k in ["qa", "test", "quality"]):
        return "QA / TEST - Testing"
    return "DEV - Development"

def predict_deployment(text):
    if not text: return "On-Premise"
    text = text.lower()
    if any(k in text for k in ["cloud", "azure", "aws", "web"]):
        return "Cloud"
    return "On-Premise"

def predict_ticket_type(text):
    if not text: return "Incident"
    text = text.lower()
    if any(k in text for k in ["request", "access", "new", "add", "create"]):
        return "Service Request"
    if any(k in text for k in ["change", "update", "modify", "alter"]):
        return "Change Request"
    return "Incident"


def predict_ticket_details_llm(text):
    res = analyze_ticket_with_ai(text)
    return res.get('fields', {})

def extract_entities_from_text(text):
    res = analyze_ticket_with_ai(text)
    return {"all_tags": res.get('tags', [])}


# Removed _fallback_tag_extraction as it is no longer necessary with advanced OCI AI tagging.


def get_partner_companies():
    """
    Returns list of known partner companies.
    """
    return [
        "CNG",
        "GLESBY", 
        "Sensanate",
        "PCB",
        "NoblQ",
        "Other (Custom...)"
    ]
