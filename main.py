from typing import Any, List
import httpx
import os
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("simplelocalize")

# Constants
SIMPLELOCALIZE_API_BASE = "https://api.simplelocalize.io"
SIMPLELOCALIZE_API_KEY = os.getenv("SIMPLELOCALIZE_API_KEY")
if not SIMPLELOCALIZE_API_KEY:
    raise ValueError("SIMPLELOCALIZE_API_KEY environment variable is not set")

class SimpleLocalizeError(Exception):
    """Custom error for SimpleLocalize API errors"""
    pass

async def make_simplelocalize_request(method: str, endpoint: str, json_data: dict | None = None) -> dict[str, Any]:
    """Make a request to the SimpleLocalize API with proper error handling."""
    headers = {
        "X-SimpleLocalize-Token": SIMPLELOCALIZE_API_KEY,
        "Content-Type": "application/json"
    }
    
    url = f"{SIMPLELOCALIZE_API_BASE}{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "POST":
                response = await client.post(url, headers=headers, json=json_data, timeout=30.0)
            elif method.upper() == "PATCH":
                response = await client.patch(url, headers=headers, json=json_data, timeout=30.0)
            elif method.upper() == "GET":
                response = await client.get(url, headers=headers, timeout=30.0)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise SimpleLocalizeError(f"SimpleLocalize API error: {str(e)}")

@mcp.tool()
async def create_translation_keys(keys: List[dict]) -> str:
    """Create translation keys in bulk for a project.
    
    This endpoint allows you to create multiple translation keys at once. You can create up to 100 translation keys in a single request.
    Each key must have a 'key' field, and optionally can include 'namespace' and 'description' fields.
    
    Args:
        keys: List of dictionaries containing key information with fields:
            - key (required): Translation key (max 500 chars)
            - namespace (optional): Namespace for the key (max 128 chars)
            - description (optional): Description for translators (max 500 chars)
    """
    # Validate and clean input
    cleaned_keys = []
    for key_info in keys:
        if not key_info.get("key"):
            raise ValueError("Each key must have a 'key' field")
            
        cleaned_key = {
            "key": key_info["key"]
        }
        
        # Only include optional fields if they exist
        if "namespace" in key_info:
            cleaned_key["namespace"] = key_info["namespace"]
        if "description" in key_info:
            cleaned_key["description"] = key_info["description"]
            
        cleaned_keys.append(cleaned_key)

    if len(cleaned_keys) > 100:
        raise ValueError("Maximum 100 keys allowed per request")

    try:
        result = await make_simplelocalize_request(
            "POST",
            "/api/v1/translation-keys/bulk",
            {"translationKeys": cleaned_keys}
        )
        
        if "failures" in result.get("data", {}):
            failures = result["data"]["failures"]
            if failures:
                return f"Some keys failed to create: {failures}"
        
        return f"Successfully created {len(cleaned_keys)} translation keys"
    except SimpleLocalizeError as e:
        return str(e)

@mcp.tool()
async def update_translations(translations: List[dict]) -> str:
    """Update translations in bulk with a single request.
    
    This endpoint allows you to update multiple translations at once. You can update up to 100 translations in a single request.
    Each translation must specify the key, language, and text. Namespace is optional.
    
    Args:
        translations: List of dictionaries containing translation information with fields:
            - key (required): Translation key
            - language (required): Language code
            - text (required): Translation text (max 65535 chars)
            - namespace (optional): Namespace for the key
    """
    # Validate and clean input
    cleaned_translations = []
    for trans in translations:
        if not all(k in trans for k in ["key", "language", "text"]):
            raise ValueError("Each translation must have 'key', 'language', and 'text' fields")
            
        cleaned_trans = {
            "key": trans["key"],
            "language": trans["language"],
            "text": trans["text"]
        }
        
        # Only include namespace if it exists
        if "namespace" in trans:
            cleaned_trans["namespace"] = trans["namespace"]
            
        cleaned_translations.append(cleaned_trans)

    if len(cleaned_translations) > 100:
        raise ValueError("Maximum 100 translations allowed per request")

    try:
        result = await make_simplelocalize_request(
            "PATCH",
            "/api/v2/translations/bulk",
            {"translations": cleaned_translations}
        )
        
        if "failures" in result.get("data", {}):
            failures = result["data"]["failures"]
            if failures:
                return f"Some translations failed to update: {failures}"
        
        return f"Successfully updated {len(cleaned_translations)} translations"
    except SimpleLocalizeError as e:
        return str(e)

@mcp.tool()
async def publish_translations(environment_key: str) -> str:
    """Publish translations to a specified environment.
    
    This endpoint publishes translations from the translation editor to hosting environments
    or from one hosting environment to another. Please note that this endpoint requires
    authorization and is only available for paid plans.
    
    Common environment keys:
    - "_latest": Publish from Translation Editor
    - "_production": Publish to production environment (from _latest by default)
    - Custom environment key: Publish to custom environment
    
    Args:
        environment_key: The environment key to publish to (e.g., "_latest", "_production", or custom key)
    """
    if not environment_key:
        raise ValueError("Environment key is required")
    
    try:
        result = await make_simplelocalize_request(
            "POST",
            f"/api/v2/environments/{environment_key}/publish"
        )
        
        return f"Successfully initiated publishing to environment '{environment_key}'. Status: {result.get('msg', 'OK')}"
    except SimpleLocalizeError as e:
        return str(e)

@mcp.tool()
async def get_environment_status(environment_key: str) -> str:
    """Get the current status of a specified environment.
    
    This endpoint returns information about the environment including the number of keys,
    languages, non-empty translations, creation date, and available resources.
    
    Args:
        environment_key: The environment key to check status for (e.g., "_latest", "_production", or custom key)
    """
    if not environment_key:
        raise ValueError("Environment key is required")
    
    try:
        result = await make_simplelocalize_request(
            "GET",
            f"/api/v2/environments/{environment_key}"
        )
        
        data = result.get("data", {})
        
        # Format the response in a readable way
        status_info = f"""Environment '{environment_key}' Status:
- Number of keys: {data.get('numberOfKeys', 0)}
- Number of languages: {data.get('numberOfLanguages', 0)}
- Non-empty translations: {data.get('numberOfNonEmptyTranslations', 0)}
- Created at: {data.get('createdAt', 'Unknown')}
- Number of resources: {len(data.get('resources', []))}"""
        
        return status_info
    except SimpleLocalizeError as e:
        return str(e)

if __name__ == "__main__":
    mcp.run(transport='stdio')
