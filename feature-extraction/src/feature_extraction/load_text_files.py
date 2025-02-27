import os
from pathlib import Path
from typing import Dict, List, Tuple

def load_features(data_dir: str | Path) -> List[str]:
    """
    Load the features list from features.txt
    
    Args:
        data_dir: Path to the data source directory
        
    Returns:
        List of feature names
    """
    features_path = Path(data_dir) / "features.txt"
    with open(features_path, "r", encoding="utf-8") as f:
        features = [line.strip() for line in f.readlines()]
    return features

def load_product_files(data_dir: str | Path) -> Dict[str, str]:
    """
    Load all product text files from the data directory
    
    Args:
        data_dir: Path to the data source directory
        
    Returns:
        Dictionary mapping product file names to their content
    """
    data_dir = Path(data_dir)
    product_files = {}
    
    for file in data_dir.glob("product_*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            product_files[file.stem] = content
            
    return product_files

def load_all_data(data_dir: str | Path) -> Tuple[List[str], Dict[str, str]]:
    """
    Load both features and product files
    
    Args:
        data_dir: Path to the data source directory
        
    Returns:
        Tuple containing:
        - List of features
        - Dictionary of product contents
    """
    features = load_features(data_dir)
    products = load_product_files(data_dir)
    return features, products

if __name__ == "__main__":
    features, products = load_all_data("data_source")
    print(features)
    print(products)


