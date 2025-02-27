from llm_config import LLMConfig
from load_text_files import load_all_data
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os
import json
import re
import pandas as pd
from pathlib import Path

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL")

def normalize_value(value: str, feature_name: str) -> Any:
    """
    Normalize feature values by removing units and standardizing formats.
    
    Args:
        value: The raw value extracted from the LLM
        feature_name: The name of the feature (to apply feature-specific normalization)
        
    Returns:
        Normalized value (could be string, int, float, etc.)
    """
    if value is None or value == "":
        return None
    
    # If value is already a number, return it as is
    if isinstance(value, (int, float)):
        return value
        
    # Make sure value is a string before calling .lower()
    if not isinstance(value, str):
        # Try to convert to string, or return as is if that's not possible
        try:
            value = str(value)
        except:
            return value
        
    # Convert "N/A", "Not specified", etc. to None
    if value.lower() in ["n/a", "not specified", "not available", "unknown", "null", "none"]:
        return None
    
    # Connection-specific normalization
    if "connection" in feature_name.lower():
        # Special case for fuel connection - make sure it's not a fuel type
        if "fuel" in feature_name.lower() and any(fuel in value.lower() for fuel in ["natural gas", "propane", "liquid gas"]):
            # This is likely a fuel type, not a connection type
            if "natural gas" in value.lower():
                if "e" in value.lower() and "ll" in value.lower():
                    return "Natural gas E/LL"
                elif "e" in value.lower() or "h" in value.lower():
                    return "Natural gas E"
                elif "ll" in value.lower() or "l" in value.lower():
                    return "Natural gas LL"
                else:
                    return "Natural gas"
            elif "propane" in value.lower() or "liquid" in value.lower():
                return "Propane/Liquid gas"
            return value.strip()
        
        # Handle flue gas connection - often just a diameter in mm
        if "flue" in feature_name.lower() and re.match(r'^\d+$', value.strip()):
            return f"{value.strip()} mm"
        
        # Handle inch connections - standardize format
        if "inch" in value.lower() or '"' in value or "\"" in value:
            match = re.search(r'(?:R|Rp)?\s*(\d+(?:/\d+)?)\s*(?:inch|"|\")', value.lower())
            if match:
                size = match.group(1)
                prefix = ""
                if "r" in value.lower() and "p" in value.lower():
                    prefix = "Rp "
                elif "r" in value.lower():
                    prefix = "R "
                return f"{prefix}{size} inch"
        
        # Handle Rp/R connections without explicit inch
        if re.search(r'(?:R|Rp)\s*(\d+(?:/\d+)?)', value):
            match = re.search(r'(R|Rp)\s*(\d+(?:/\d+)?)', value)
            if match:
                prefix = match.group(1)
                size = match.group(2)
                return f"{prefix} {size} inch"
        
        # Handle DN connections
        if re.search(r'(?:DN|dn)\s*(\d+)', value):
            match = re.search(r'(?:DN|dn)\s*(\d+)', value)
            if match:
                return f"DN {match.group(1)}"
        
        # If it's just a number for a connection, assume it's mm diameter
        if re.match(r'^\d+$', value.strip()):
            return f"{value.strip()} mm"
    
    # Handle dimensions and measurements
    if any(unit in feature_name.lower() for unit in ["width", "height", "depth", "volume", "weight"]):
        # Extract numeric value from strings like "840 mm" or "47.5 kg"
        match = re.search(r'([\d.]+)', value)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    
    # Handle percentages
    if "%" in value or "percent" in value.lower() or "efficiency" in feature_name.lower():
        match = re.search(r'([\d.]+)', value)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    
    # Handle power values
    if "kW" in value or "power" in feature_name.lower():
        match = re.search(r'([\d.]+)', value)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    
    # Handle temperature values
    if "°C" in value or "temperature" in feature_name.lower():
        match = re.search(r'([\d.]+)', value)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    
    # Handle pressure values
    if "bar" in value or "mbar" in value or "pressure" in feature_name.lower():
        if "mbar" in value:
            match = re.search(r'([\d.]+)\s*mbar', value)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        else:
            match = re.search(r'([\d.]+)\s*bar', value)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
    
    # Handle boolean values
    if value.lower() in ["yes", "true", "available", "included", "suitable"]:
        return True
    if value.lower() in ["no", "false", "not available", "not included", "not suitable"]:
        return False
    
    # Handle fuel types - standardize format
    if "fuel" in feature_name.lower() or "gas" in feature_name.lower():
        # Standardize natural gas naming
        if "natural gas" in value.lower():
            if "e" in value.lower() and "ll" in value.lower():
                return "Natural gas E/LL"
            elif "e" in value.lower() or "h" in value.lower():
                return "Natural gas E"
            elif "ll" in value.lower() or "l" in value.lower():
                return "Natural gas LL"
            else:
                return "Natural gas"
        elif "propane" in value.lower() or "liquid" in value.lower():
            return "Propane/Liquid gas"
    
    # Default: return the original value with proper capitalization for readability
    if isinstance(value, str) and len(value) > 0:
        # Capitalize first letter of each word for better presentation
        return ' '.join(word.capitalize() for word in value.split())
    
    return value

def parse_llm_response(response: str) -> Dict[str, Any]:
    """
    Parse the LLM response and extract the feature values.
    
    Args:
        response: The raw response from the LLM
        
    Returns:
        Dictionary of feature values
    """
    # Clean the response - remove markdown code blocks if present
    cleaned_response = response
    if "```json" in response:
        # Extract content between ```json and ```
        match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            cleaned_response = match.group(1)
    elif "```" in response:
        # Extract content between ``` and ```
        match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            cleaned_response = match.group(1)
    
    try:
        # Try to parse as JSON
        data = json.loads(cleaned_response)
        return data
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Attempted to parse: {cleaned_response[:200]}...")
        
        # Try to extract JSON from the response if it's embedded in text
        json_pattern = r'({.*})'
        match = re.search(json_pattern, cleaned_response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return data
            except json.JSONDecodeError:
                pass
        
        # If not valid JSON, try to extract key-value pairs from text
        result = {}
        lines = cleaned_response.strip().split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
        
        # If we found some key-value pairs, return them
        if result:
            return result
            
        # Last resort: try to find any JSON-like structure
        potential_json = re.search(r'({[\s\S]*})', cleaned_response)
        if potential_json:
            try:
                # Try to clean and parse it
                fixed_json = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', potential_json.group(1))
                data = json.loads(fixed_json)
                return data
            except json.JSONDecodeError:
                pass
        
        # If all else fails, return an empty dict
        print("Failed to parse response as JSON or key-value pairs")
        return {}

def extract_features(features: list[str], products: dict[str, str], output_dir: str = "output") -> dict[str, dict[str, Any]]:
    """
    Extract features from product descriptions and save to XLSX files
    
    Args:
        features: List of feature names to extract
        products: Dictionary of product_id -> product description
        output_dir: Directory to save the XLSX files
        
    Returns:
        Dictionary mapping product_ids to their extracted features
    """
    llm_config = LLMConfig(openai_model)
    results = {}
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Debug: Print the number of products and their IDs
    print(f"Processing {len(products)} products: {list(products.keys())}")
    
    # Process each product
    for product_id, product_text in products.items():
        # Debug: Print product ID and text length
        print(f"Extracting features for {product_id} (text length: {len(product_text)})")
        
        prompt = f"""
        Extract the following features from this product description. 
        Only extract features that are explicitly mentioned in the text.
        If a feature is not mentioned, set its value to null.
        
        For numeric values, extract only the number without units (e.g., for "840 mm" extract "840").
        For ranges, extract the maximum value unless otherwise specified.
        For connection types like "R 3/4 inch", extract only the connection type and size without units (e.g., "R 3/4").
        
        Features to extract: {', '.join(features)}
        
        Product description:
        {product_text}

        Return the features in a valid JSON format like this:
        {{
            "feature1": "value1",
            "feature2": 123,
            "feature3": null
        }}
        
        Only include features from the provided list. Do not add any explanations or notes outside the JSON.
        """
        
        # Get response from LLM
        response = llm_config.get_llm_response(prompt)
        
        # Debug: Print a snippet of the response
        print(f"Response snippet for {product_id}: {response[:100]}...")
        
        # Parse the response
        extracted_data = parse_llm_response(response)
        
        # Debug: Print the number of extracted features
        print(f"Extracted {len(extracted_data)} features for {product_id}")
        
        # Normalize the values and strip units for display
        normalized_data = {}
        for feature in features:
            if feature in extracted_data:
                value = extracted_data[feature]
                # Normalize the value first
                normalized_value = normalize_value(value, feature)
                # Then strip units for display
                display_value = strip_units(normalized_value)
                normalized_data[feature] = display_value
            else:
                normalized_data[feature] = None
        
        results[product_id] = normalized_data
        
        # Save to XLSX
        df = pd.DataFrame([normalized_data])
        df.to_excel(output_path / f"{product_id}.xlsx", index=False)
        
        print(f"Processed {product_id}")
        
    return results

def strip_units(value: Any) -> Any:
    """
    Strip units from normalized values for display purposes.
    
    Args:
        value: The normalized value
        
    Returns:
        Value with units removed
    """
    if value is None:
        return None
        
    if isinstance(value, (int, float, bool)):
        return value
        
    if not isinstance(value, str):
        return value
        
    # Handle connection types (R 3/4 inch -> R 3/4)
    if "inch" in value:
        return value.replace(" inch", "").strip()
        
    # Handle mm measurements (80 mm -> 80)
    if " mm" in value:
        return value.replace(" mm", "").strip()
        
    # Handle DN connections (DN 80 -> DN 80)
    if value.startswith("DN "):
        return value
        
    # Handle other units that might be present
    for unit in [" bar", " mbar", " °C", " kW", " kg", " l", " m", " cm"]:
        if unit in value:
            return value.replace(unit, "").strip()
            
    return value

def main():
    # Debug: Print when main function starts
    print("Starting feature extraction process")
    
    # Load data
    features, products = load_all_data("data_source")
    
    # Debug: Print loaded features and products
    print(f"Loaded {len(features)} features and {len(products)} products")
    
    # Extract features
    extracted_features = extract_features(features, products)
    
    # Save all results to a single file as well
    all_results = []
    for product_id, features in extracted_features.items():
        product_data = {"product_id": product_id}
        product_data.update(features)
        all_results.append(product_data)
    
    df = pd.DataFrame(all_results)
    df.to_excel("output/all_products.xlsx", index=False)
    
    print(f"Processed {len(products)} products. Results saved to output directory.")

if __name__ == "__main__":
    main()




