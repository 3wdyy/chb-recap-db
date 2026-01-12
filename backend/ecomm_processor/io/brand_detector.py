"""Brand detection from filenames."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config_models import BrandConfig


class BrandDetector:
    """
    Detects brand from filename using configured patterns.

    Supports:
    - Exact pattern matching
    - Case-insensitive matching
    - Multiple patterns per brand
    """

    def __init__(self, brand_configs: dict[str, BrandConfig]):
        """
        Initialize the detector.

        Args:
            brand_configs: Dictionary of brand name -> config
        """
        self.brand_configs = brand_configs
        self._build_pattern_index()

    def _build_pattern_index(self) -> None:
        """Build an index of patterns to brand names."""
        self._pattern_index: dict[str, str] = {}

        for brand_name, config in self.brand_configs.items():
            for pattern in config.filename_patterns:
                self._pattern_index[pattern.upper()] = brand_name

    def detect(self, filename: str) -> str | None:
        """
        Detect brand from filename.

        Args:
            filename: Filename (with or without path)

        Returns:
            Brand name if detected, None otherwise
        """
        # Get just the filename without path
        filename_only = filename.split("/")[-1].split("\\")[-1]
        filename_upper = filename_only.upper()

        # Check each pattern
        for pattern, brand_name in self._pattern_index.items():
            if pattern in filename_upper:
                # Verify brand is enabled
                config = self.brand_configs.get(brand_name)
                if config and config.brand.enabled:
                    return brand_name

        return None

    def detect_all(self, filenames: list[str]) -> dict[str, str | None]:
        """
        Detect brands for multiple filenames.

        Args:
            filenames: List of filenames

        Returns:
            Dictionary of filename -> detected brand name (or None)
        """
        return {filename: self.detect(filename) for filename in filenames}

    def get_patterns_for_brand(self, brand_name: str) -> list[str]:
        """Get filename patterns for a brand."""
        config = self.brand_configs.get(brand_name)
        if config:
            return config.filename_patterns
        return []

    def list_enabled_brands(self) -> list[str]:
        """List all enabled brands."""
        return [
            name for name, config in self.brand_configs.items()
            if config.brand.enabled
        ]
