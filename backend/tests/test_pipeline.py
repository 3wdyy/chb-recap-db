"""
End-to-end tests for the processing pipeline.

Tests each brand configuration with sample data to ensure
the transformations work correctly.
"""

import pandas as pd
import pytest
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ecomm_processor.core.config_loader import ConfigLoader
from ecomm_processor.core.pipeline_engine import PipelineEngine
from ecomm_processor.io.file_reader import FileReader
from ecomm_processor.io.file_writer import FileWriter


@pytest.fixture
def config_loader():
    """Create config loader with test configs."""
    config_dir = Path(__file__).parent.parent / "config"
    return ConfigLoader(config_dir)


@pytest.fixture
def engine(config_loader):
    """Create pipeline engine."""
    return PipelineEngine(config_loader.global_config)


class TestGhawali:
    """Test Ghawali (Shopify) brand processing."""

    def get_sample_data(self):
        """Create sample Ghawali data."""
        return pd.DataFrame({
            "Fulfillment Status": ["fulfilled", "fulfilled", "pending"],
            "Fulfilled at": ["2025-11-15 10:30:00", "2025-11-16 14:45:00", "2025-11-17 09:00:00"],
            "Currency": ["AED", "SAR", "AED"],
            "Name": ["#1001", "#1002", "#1003"],
            "Shipping Country": ["United Arab Emirates", "Saudi Arabia", "United Arab Emirates"],
            "Shipping Phone": ["501234567", "551234567", "509876543"],
            "Subtotal": [100.0, 200.0, 150.0],
            "Taxes": [5.0, 30.0, 7.5],
        })

    def test_filter_fulfilled(self, config_loader, engine):
        """Test that only fulfilled orders are processed."""
        brand_config = config_loader.get_brand_config("Ghawali")
        assert brand_config is not None

        df = self.get_sample_data()
        output_df, result = engine.process(df, brand_config)

        assert output_df is not None
        assert len(output_df) == 2  # Only fulfilled orders
        assert result.success

    def test_location_mapping(self, config_loader, engine):
        """Test currency-based location mapping."""
        brand_config = config_loader.get_brand_config("Ghawali")
        df = self.get_sample_data()
        output_df, result = engine.process(df, brand_config)

        assert output_df is not None
        locations = output_df["h_location"].tolist()
        assert 13010 in locations  # AED location
        assert 13009 in locations  # SAR location

    def test_tax_calculation(self, config_loader, engine):
        """Test tax subtraction."""
        brand_config = config_loader.get_brand_config("Ghawali")
        df = self.get_sample_data()
        output_df, result = engine.process(df, brand_config)

        assert output_df is not None
        # First row: 100 - 5 = 95
        assert output_df["h_bit_amount"].iloc[0] == 95.0


class TestTumi:
    """Test Tumi (Salesforce with aggregation) brand processing."""

    def get_sample_data(self):
        """Create sample Tumi line-item data."""
        return pd.DataFrame({
            "OrderNo": ["TUAE001", "TUAE001", "TUSA002", "TUSA002", "TUSA002"],
            "Date created": ["15.11.2025 10:30", "15.11.2025 10:30", "16.11.2025 14:45", "16.11.2025 14:45", "16.11.2025 14:45"],
            "Total": [500.0, 500.0, 750.0, 750.0, 750.0],  # Repeated header value
            "Tax": [10.0, 15.0, 20.0, 30.0, 25.0],  # Distributed across lines
            "Shipping Country": ["United Arab Emirates", "United Arab Emirates", "Saudi Arabia", "Saudi Arabia", "Saudi Arabia"],
            "Shipping Phone": ["501234567", "501234567", "551234567", "551234567", "551234567"],
            "Payment Status": ["PAID", "PAID", "PAID", "PAID", "PAID"],
        })

    def test_aggregation(self, config_loader, engine):
        """Test line-item aggregation to order level."""
        brand_config = config_loader.get_brand_config("Tumi")
        assert brand_config is not None

        df = self.get_sample_data()
        output_df, result = engine.process(df, brand_config)

        assert output_df is not None
        assert len(output_df) == 2  # Two unique orders
        assert result.success

    def test_order_prefix_location(self, config_loader, engine):
        """Test order prefix-based location mapping."""
        brand_config = config_loader.get_brand_config("Tumi")
        df = self.get_sample_data()
        output_df, result = engine.process(df, brand_config)

        assert output_df is not None
        # TUAE -> 32028, TUSA -> 32029
        locations = output_df["h_location"].tolist()
        assert 32028 in locations
        assert 32029 in locations

    def test_tax_aggregation(self, config_loader, engine):
        """Test that tax is summed across line items."""
        brand_config = config_loader.get_brand_config("Tumi")
        df = self.get_sample_data()
        output_df, result = engine.process(df, brand_config)

        assert output_df is not None
        # Order TUAE001: Total=500, Tax=10+15=25, Amount=475
        # Order TUSA002: Total=750, Tax=20+30+25=75, Amount=675
        amounts = sorted(output_df["h_bit_amount"].tolist())
        assert amounts == [475.0, 675.0]


class TestLacoste:
    """Test Lacoste (USD conversion) brand processing."""

    def get_sample_data(self):
        """Create sample Lacoste data with USD amounts."""
        return pd.DataFrame({
            "Country": ["United Arab Emirates", "Saudi Arabia", "Kuwait", "France"],
            "Record Date": ["2025-11-15", "2025-11-16", "2025-11-17", "2025-11-18"],
            "Order ID": ["LC001", "LC002", "LC003", "LC004"],
            "Contact Number": ["501234567", "551234567", "901234567", "123456789"],
            "Gross Revenue (USD)": ["$100.00", "$200.00", "$150.00", "$300.00"],
        })

    def test_country_filter(self, config_loader, engine):
        """Test that only supported countries are processed."""
        brand_config = config_loader.get_brand_config("Lacoste")
        assert brand_config is not None

        df = self.get_sample_data()
        output_df, result = engine.process(df, brand_config)

        assert output_df is not None
        assert len(output_df) == 3  # France filtered out
        assert result.success

    def test_currency_conversion(self, config_loader, engine):
        """Test USD to local currency conversion."""
        brand_config = config_loader.get_brand_config("Lacoste")
        df = self.get_sample_data()
        output_df, result = engine.process(df, brand_config)

        assert output_df is not None
        # UAE: $100 * 3.67 = 367 AED
        uae_row = output_df[output_df["h_bit_currency"] == "AED"]
        assert len(uae_row) == 1
        assert abs(uae_row["h_original_bit_amount"].iloc[0] - 367.0) < 0.01


class TestJacquemus:
    """Test Jacquemus (no filter, order prefix) brand processing."""

    def get_sample_data(self):
        """Create sample Jacquemus data."""
        return pd.DataFrame({
            "OrderNo": ["JQAE001", "JQSA002", "JQAE003"],
            "Date created": ["15.11.2025 10:30", "16.11.2025 14:45", "17.11.2025 09:00"],
            "Shipping Country": ["United Arab Emirates", "Saudi Arabia", "United Arab Emirates"],
            "Shipping Phone": ["501234567", "551234567", "509876543"],
            "Order Total Including VAT": [500.0, 750.0, 300.0],
            "Order Total Excluding VAT": [476.19, 652.17, 285.71],
        })

    def test_no_filter(self, config_loader, engine):
        """Test that all rows are processed (no filter)."""
        brand_config = config_loader.get_brand_config("Jacquemus")
        assert brand_config is not None

        df = self.get_sample_data()
        output_df, result = engine.process(df, brand_config)

        assert output_df is not None
        assert len(output_df) == 3  # All rows
        assert result.success

    def test_pre_calculated_tax(self, config_loader, engine):
        """Test pre-calculated tax amount handling."""
        brand_config = config_loader.get_brand_config("Jacquemus")
        df = self.get_sample_data()
        output_df, result = engine.process(df, brand_config)

        assert output_df is not None
        # First row: pre-calculated = 476.19
        assert abs(output_df["h_bit_amount"].iloc[0] - 476.19) < 0.01


class TestPhoneFormatting:
    """Test phone number formatting across brands."""

    def test_uae_phone(self, config_loader, engine):
        """Test UAE phone formatting."""
        brand_config = config_loader.get_brand_config("Ghawali")

        df = pd.DataFrame({
            "Fulfillment Status": ["fulfilled"],
            "Fulfilled at": ["2025-11-15 10:30:00"],
            "Currency": ["AED"],
            "Name": ["#1001"],
            "Shipping Country": ["United Arab Emirates"],
            "Shipping Phone": ["501234567"],
            "Subtotal": [100.0],
            "Taxes": [5.0],
        })

        output_df, result = engine.process(df, brand_config)
        assert output_df is not None
        assert output_df["h_mobile_number"].iloc[0] == "+971501234567"

    def test_saudi_phone(self, config_loader, engine):
        """Test Saudi phone formatting."""
        brand_config = config_loader.get_brand_config("Ghawali")

        df = pd.DataFrame({
            "Fulfillment Status": ["fulfilled"],
            "Fulfilled at": ["2025-11-15 10:30:00"],
            "Currency": ["SAR"],
            "Name": ["#1001"],
            "Shipping Country": ["Saudi Arabia"],
            "Shipping Phone": ["551234567"],
            "Subtotal": [100.0],
            "Taxes": [15.0],
        })

        output_df, result = engine.process(df, brand_config)
        assert output_df is not None
        assert output_df["h_mobile_number"].iloc[0] == "+966551234567"


class TestConfigLoader:
    """Test configuration loading."""

    def test_load_global_config(self, config_loader):
        """Test loading global configuration."""
        config = config_loader.global_config
        assert config is not None
        assert "United Arab Emirates" in config.conversion_rates
        assert config.conversion_rates["United Arab Emirates"] == 3.67

    def test_load_all_brands(self, config_loader):
        """Test loading all brand configurations."""
        brands = config_loader.load_all_brands()
        assert len(brands) >= 8

        expected_brands = [
            "Ghawali", "Tumi", "Lacoste", "Farm Rio",
            "Jacquemus", "Yeda", "Elemis", "Axel Arigato"
        ]
        for brand in expected_brands:
            assert brand in brands, f"Missing brand: {brand}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
