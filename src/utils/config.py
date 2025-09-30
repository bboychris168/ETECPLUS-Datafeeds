"""
Configuration management for ETEC+ Datafeeds application.
Handles loading and saving of application settings and configurations.
"""

import json
import os
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages configuration files for the application."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = base_path
        self.mappings_dir = os.path.join(base_path, "mappings")
        self.ensure_directories()
    
    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        os.makedirs(self.mappings_dir, exist_ok=True)
    
    def load_supplier_config(self) -> Dict[str, Any]:
        """Load supplier download configuration."""
        config_path = os.path.join(self.base_path, "supplier_config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_supplier_config(self, config: Dict[str, Any]) -> None:
        """Save supplier download configuration."""
        config_path = os.path.join(self.base_path, "supplier_config.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
    
    def load_shopify_template(self) -> list:
        """Load Shopify CSV template fields from config file."""
        template_path = os.path.join(self.mappings_dir, "shopify_template.json")
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                template_data = json.load(f)
                return template_data.get("columns", [])
        return []
    
    def save_shopify_template(self, columns: list) -> None:
        """Save Shopify CSV template columns to config file."""
        import pandas as pd
        template_data = {
            "columns": columns,
            "uploaded_date": pd.Timestamp.now().isoformat()
        }
        template_path = os.path.join(self.mappings_dir, "shopify_template.json")
        with open(template_path, 'w') as f:
            json.dump(template_data, f, indent=2)
    
    def load_mappings(self) -> Dict[str, Dict[str, str]]:
        """Load supplier mappings."""
        mappings_path = os.path.join(self.mappings_dir, "supplier_mappings.json")
        if os.path.exists(mappings_path):
            with open(mappings_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_mappings(self, mappings: Dict[str, Dict[str, str]]) -> None:
        """Save supplier mappings."""
        mappings_path = os.path.join(self.mappings_dir, "supplier_mappings.json")
        with open(mappings_path, 'w') as f:
            json.dump(mappings, f, indent=2)
    
    def load_tag_mapping(self) -> Dict[str, Any]:
        """Load tag generation configuration."""
        tag_config_path = os.path.join(self.mappings_dir, "tag_config.json")
        if os.path.exists(tag_config_path):
            with open(tag_config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_tag_mapping(self, tag_config: Dict[str, Any]) -> None:
        """Save tag generation configuration."""
        tag_config_path = os.path.join(self.mappings_dir, "tag_config.json")
        with open(tag_config_path, 'w') as f:
            json.dump(tag_config, f, indent=2)