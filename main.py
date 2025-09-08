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

@mcp.tool()
async def duplicate_translation(from_dict: dict, to_dict: dict) -> str:
    """Duplicate translations from one key/namespace to another key/namespace.
    
    This function copies all translations for a specific key (and optionally namespace)
    to another key (and optionally namespace). Useful for duplicating translations
    when creating similar keys or reorganizing translations.
    
    Args:
        from_dict: Source dictionary with fields:
            - key (required): Source translation key
            - namespace (optional): Source namespace
        to_dict: Destination dictionary with fields:
            - key (required): Destination translation key
            - namespace (optional): Destination namespace
    
    Returns:
        String message indicating success or failure
    """
    # Validate input
    if not from_dict.get("key"):
        raise ValueError("Source dictionary must have a 'key' field")
    if not to_dict.get("key"):
        raise ValueError("Destination dictionary must have a 'key' field")
    
    source_key = from_dict["key"]
    source_namespace = from_dict.get("namespace", "")
    dest_key = to_dict["key"]
    dest_namespace = to_dict.get("namespace", "")
    
    try:
        # Step 1: Get all translations from the source
        result = await make_simplelocalize_request(
            "GET",
            "/api/v2/translations"
        )
        
        data = result.get("data", [])
        
        # Filter for translations matching the source key/namespace
        source_translations = []
        for item in data:
            key = item.get("key", "")
            namespace = item.get("namespace", "")
            language = item.get("language", "")
            text = item.get("text", "")
            
            # Check if this matches our source key/namespace
            if key == source_key and namespace == source_namespace and text:
                source_translations.append({
                    "language": language,
                    "text": text
                })
        
        if not source_translations:
            return f"No translations found for key '{source_key}'" + (f" in namespace '{source_namespace}'" if source_namespace else "")
        
        # Step 2: Create the destination key if it doesn't exist
        create_key_payload = {
            "key": dest_key
        }
        if dest_namespace:
            create_key_payload["namespace"] = dest_namespace
        
        # Try to create the key (will fail silently if it already exists)
        try:
            await make_simplelocalize_request(
                "POST",
                "/api/v1/translation-keys/bulk",
                {"translationKeys": [create_key_payload]}
            )
        except SimpleLocalizeError:
            # Key might already exist, continue
            pass
        
        # Step 3: Copy all translations to the destination
        translations_to_update = []
        for trans in source_translations:
            update_payload = {
                "key": dest_key,
                "language": trans["language"],
                "text": trans["text"]
            }
            if dest_namespace:
                update_payload["namespace"] = dest_namespace
            translations_to_update.append(update_payload)
        
        # Update translations in bulk
        update_result = await make_simplelocalize_request(
            "PATCH",
            "/api/v2/translations/bulk",
            {"translations": translations_to_update}
        )
        
        if "failures" in update_result.get("data", {}):
            failures = update_result["data"]["failures"]
            if failures:
                return f"Some translations failed to duplicate: {failures}"
        
        source_desc = f"'{source_key}'" + (f" (namespace: '{source_namespace}')" if source_namespace else "")
        dest_desc = f"'{dest_key}'" + (f" (namespace: '{dest_namespace}')" if dest_namespace else "")
        
        return f"Successfully duplicated {len(translations_to_update)} translation(s) from {source_desc} to {dest_desc}"
        
    except SimpleLocalizeError as e:
        return str(e)

@mcp.tool()
async def get_missing_translations() -> List[dict]:
    """Get a list of translation keys that have missing translations.
    
    This endpoint returns translation keys along with their existing translations,
    focusing on keys that are missing translations in one or more languages.
    To identify missing translations, the function compares each key against all
    languages that have at least one translation in the project.
    
    Returns:
        List of dictionaries containing:
            - key (str): Translation key
            - namespace (str): Namespace for the key (if applicable)
            - description (str): Description for translators (if applicable)
            - translations (List[dict]): List of existing translations with fields:
                - language (str): Language code
                - text (str): Translation text
    """
    try:
        # Get all translation keys with their translations
        result = await make_simplelocalize_request(
            "GET",
            "/api/v2/translations"
        )
        
        data = result.get("data", [])
        
        # First pass: collect all languages used in the project
        all_languages = set()
        keys_map = {}
        
        for item in data:
            key = item.get("key", "")
            namespace = item.get("namespace", "")
            description = item.get("description", "")
            language = item.get("language", "")
            text = item.get("text", "")
            
            if language:
                all_languages.add(language)
            
            # Create a unique identifier for the key (including namespace)
            key_id = f"{namespace}:{key}" if namespace else key
            
            if key_id not in keys_map:
                keys_map[key_id] = {
                    "key": key,
                    "namespace": namespace,
                    "description": description,
                    "translations": [],
                    "languages_with_translations": set()
                }
            
            # Add translation if text exists
            if text and language:
                keys_map[key_id]["translations"].append({
                    "language": language,
                    "text": text
                })
                keys_map[key_id]["languages_with_translations"].add(language)
        
        # Second pass: filter for keys that have missing translations
        missing_translations = []
        
        for key_data in keys_map.values():
            # Check if this key is missing translations in any language
            missing_languages = all_languages - key_data["languages_with_translations"]
            
            # Only include keys that have missing translations
            if missing_languages:
                # Remove the helper set before returning
                key_result = {
                    "key": key_data["key"],
                    "namespace": key_data["namespace"],
                    "description": key_data["description"],
                    "translations": key_data["translations"]
                }
                missing_translations.append(key_result)
        
        if len(missing_translations) == 0:
            return "No missing translations found"
        
        return missing_translations
        
    except SimpleLocalizeError as e:
        return [{"error": str(e)}]

@mcp.tool()
async def get_translations_for_keys(keys: List[str], namespace: str = None) -> List[dict]:
    """Get translations for specific translation keys.
    
    This endpoint fetches translations for a list of specified keys, optionally filtered by namespace.
    Returns all available translations for each key across all languages in the project.
    
    Args:
        keys: List of translation keys to fetch translations for (required)
        namespace: Optional namespace to filter the translations (if not provided, fetches from all namespaces)
    
    Returns:
        List of dictionaries containing:
            - key (str): Translation key
            - namespace (str): Namespace for the key
            - translations (List[dict]): List of translations with fields:
                - language (str): Language code  
                - text (str): Translation text
                - reviewStatus (str): Review status (REVIEWED, NOT_REVIEWED)
                - lastModifiedAt (str): Last modification timestamp
    """
    if not keys:
        raise ValueError("At least one key is required")
    
    try:
        # Build query parameters for fetching all translations
        endpoint = "/api/v2/translations"
        params = []
        
        # If namespace is specified, add it to the query
        if namespace:
            params.append(f"namespace={namespace}")
        
        # Add size parameter to get more results (max 500 per API docs)
        params.append("size=500")
        
        # Build full endpoint URL with query parameters
        if params:
            endpoint += "?" + "&".join(params)
        
        result = await make_simplelocalize_request("GET", endpoint)
        
        data = result.get("data", [])
        
        # Create a set for faster lookup
        keys_set = set(keys)
        
        # Group translations by key and namespace
        keys_map = {}
        
        for item in data:
            item_key = item.get("key", "")
            item_namespace = item.get("namespace", "")
            language = item.get("language", "")
            text = item.get("text", "")
            review_status = item.get("reviewStatus", "")
            last_modified_at = item.get("lastModifiedAt", "")
            
            # Only include if the key is in our requested keys list
            if item_key in keys_set:
                # If namespace filter is specified, only include matching items
                if namespace is not None and item_namespace != namespace:
                    continue
                    
                # Create a unique identifier for the key/namespace combination
                key_id = f"{item_namespace}:{item_key}" if item_namespace else item_key
                
                if key_id not in keys_map:
                    keys_map[key_id] = {
                        "key": item_key,
                        "namespace": item_namespace,
                        "translations": []
                    }
                
                # Add translation if it has content
                if text and language:
                    keys_map[key_id]["translations"].append({
                        "language": language,
                        "text": text,
                        "reviewStatus": review_status,
                        "lastModifiedAt": last_modified_at
                    })
        
        # Convert to list and ensure we have entries for all requested keys
        results = []
        for key in keys:
            # Check both with and without namespace
            key_id = f"{namespace}:{key}" if namespace else key
            key_id_no_namespace = key
            
            if key_id in keys_map:
                results.append(keys_map[key_id])
            elif key_id_no_namespace in keys_map:
                results.append(keys_map[key_id_no_namespace])
            else:
                # Add empty entry for keys that don't have translations
                results.append({
                    "key": key,
                    "namespace": namespace or "",
                    "translations": []
                })
        
        return results
        
    except SimpleLocalizeError as e:
        return [{"error": str(e)}]

if __name__ == "__main__":
    mcp.run(transport='stdio')
