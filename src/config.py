import yaml
import os
import logging

class Config:
    """Handles loading and parsing of the YAML configuration file."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initializes the configuration object.
        
        Args:
            config_path (str): Path to the YAML configuration file.
        """
        self.config_path = config_path
        self.settings = self._load_config()

    def _load_config(self) -> dict:
        """Loads the YAML file."""
        if not os.path.exists(self.config_path):
            logging.warning(f"Config file {self.config_path} not found. Using defaults.")
            return {}
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def get(self, key: str, default=None):
        """
        Retrieves a configuration value, allowing nested keys via dot notation.
        
        Args:
            key (str): The configuration key (e.g., 'optimization.method').
            default: The default value if the key is not found.
        """
        keys = key.split('.')
        value = self.settings
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value