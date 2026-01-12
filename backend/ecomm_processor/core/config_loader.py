"""
Configuration loader for YAML-based configs.

Handles loading, validation, and caching of global and brand configurations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .config_models import BrandConfig, GlobalConfig


class ConfigLoader:
    """
    Loads and manages configuration from YAML files.

    Supports:
    - Global config from global_config.yaml
    - Brand configs from brands/*.yaml
    - In-memory config updates for API
    """

    def __init__(self, config_dir: str | Path | None = None):
        """
        Initialize the config loader.

        Args:
            config_dir: Path to config directory. Defaults to ./config
        """
        if config_dir is None:
            # Default to config dir relative to this file's package
            config_dir = Path(__file__).parent.parent.parent / "config"

        self.config_dir = Path(config_dir)
        self._global_config: GlobalConfig | None = None
        self._brand_configs: dict[str, BrandConfig] = {}

    @property
    def global_config(self) -> GlobalConfig:
        """Get the global configuration (lazy loaded)."""
        if self._global_config is None:
            self._global_config = self._load_global_config()
        return self._global_config

    def _load_global_config(self) -> GlobalConfig:
        """Load global configuration from YAML file."""
        config_path = self.config_dir / "global_config.yaml"

        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            return GlobalConfig(**data)

        # Return defaults if no config file exists
        return GlobalConfig()

    def get_brand_config(self, brand_name: str) -> BrandConfig | None:
        """
        Get configuration for a specific brand.

        Args:
            brand_name: Brand name to load config for

        Returns:
            BrandConfig if found, None otherwise
        """
        # Check cache first
        if brand_name in self._brand_configs:
            return self._brand_configs[brand_name]

        # Try to load from file
        config = self._load_brand_config(brand_name)
        if config:
            self._brand_configs[brand_name] = config

        return config

    def _load_brand_config(self, brand_name: str) -> BrandConfig | None:
        """Load brand configuration from YAML file."""
        brands_dir = self.config_dir / "brands"

        if not brands_dir.exists():
            return None

        # Try different filename patterns
        filename_patterns = [
            f"{brand_name.lower()}.yaml",
            f"{brand_name.lower().replace(' ', '_')}.yaml",
            f"{brand_name.lower().replace(' ', '-')}.yaml",
        ]

        for pattern in filename_patterns:
            config_path = brands_dir / pattern
            if config_path.exists():
                with open(config_path) as f:
                    data = yaml.safe_load(f) or {}
                return BrandConfig(**data)

        return None

    def list_brands(self) -> list[str]:
        """List all available brand configurations."""
        brands_dir = self.config_dir / "brands"

        if not brands_dir.exists():
            return []

        brands = []
        for path in brands_dir.glob("*.yaml"):
            try:
                with open(path) as f:
                    data = yaml.safe_load(f) or {}
                if "brand" in data and "name" in data["brand"]:
                    brands.append(data["brand"]["name"])
            except Exception:
                continue

        return sorted(brands)

    def load_all_brands(self) -> dict[str, BrandConfig]:
        """Load all brand configurations."""
        brands_dir = self.config_dir / "brands"

        if not brands_dir.exists():
            return {}

        configs = {}
        for path in brands_dir.glob("*.yaml"):
            try:
                with open(path) as f:
                    data = yaml.safe_load(f) or {}
                config = BrandConfig(**data)
                configs[config.brand.name] = config
                self._brand_configs[config.brand.name] = config
            except Exception as e:
                print(f"Warning: Failed to load {path}: {e}")
                continue

        return configs

    def save_global_config(self, config: GlobalConfig) -> None:
        """Save global configuration to YAML file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        config_path = self.config_dir / "global_config.yaml"

        data = config.model_dump(exclude_none=True)
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        self._global_config = config

    def save_brand_config(self, config: BrandConfig) -> None:
        """Save brand configuration to YAML file."""
        brands_dir = self.config_dir / "brands"
        brands_dir.mkdir(parents=True, exist_ok=True)

        filename = config.brand.name.lower().replace(" ", "_") + ".yaml"
        config_path = brands_dir / filename

        data = config.model_dump(exclude_none=True)
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        self._brand_configs[config.brand.name] = config

    def delete_brand_config(self, brand_name: str) -> bool:
        """Delete a brand configuration file."""
        brands_dir = self.config_dir / "brands"

        # Find and delete the file
        filename_patterns = [
            f"{brand_name.lower()}.yaml",
            f"{brand_name.lower().replace(' ', '_')}.yaml",
            f"{brand_name.lower().replace(' ', '-')}.yaml",
        ]

        deleted = False
        for pattern in filename_patterns:
            config_path = brands_dir / pattern
            if config_path.exists():
                config_path.unlink()
                deleted = True

        # Remove from cache
        if brand_name in self._brand_configs:
            del self._brand_configs[brand_name]

        return deleted

    def update_global_config(self, updates: dict[str, Any]) -> GlobalConfig:
        """Update global configuration with partial data."""
        current = self.global_config.model_dump()
        current.update(updates)
        new_config = GlobalConfig(**current)
        self.save_global_config(new_config)
        return new_config

    def reload(self) -> None:
        """Reload all configurations from disk."""
        self._global_config = None
        self._brand_configs = {}

    def detect_brand_from_filename(self, filename: str) -> str | None:
        """
        Detect brand from filename using configured patterns.

        Args:
            filename: Name of the file (without path)

        Returns:
            Brand name if matched, None otherwise
        """
        filename_upper = filename.upper()

        # Load all brands to check patterns
        brands = self.load_all_brands()

        for brand_name, config in brands.items():
            for pattern in config.filename_patterns:
                if pattern.upper() in filename_upper:
                    return brand_name

        return None
