"""
Configuration management for the Excel Processing System.
Provides functionality for loading and managing configuration from various sources.
"""

from excel_db_excel_v2.config.config_manager import ExcelProcessorConfig
from excel_db_excel_v2.config.defaults import DEFAULT_CONFIG

__all__ = ['ExcelProcessorConfig', 'DEFAULT_CONFIG']