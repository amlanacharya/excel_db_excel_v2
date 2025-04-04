import argparse
import configparser
import os
import json
from typing import Dict, Set, List, Any, Optional

class ExcelProcessorConfig:
    """Configuration manager for the Excel Processing System.
    Follows the Single Responsibility Principle by focusing only on configuration management.
    """
    def __init__(self, config_file: Optional[str] = None):
        # Set default values
        self.config = {
            # General configuration
            'excel_files': ["Deposits Data Lite.xlsx", "Form X Report  Main Lite.xlsx", "Loans Data Lite.xlsx"],
            'report_sheets': {"Part I", "Part II", "Part III", "MIS-Report"},
            'exclude_sheets': {"Pivot-Borrowings"},
            'db_filename': "excel_data.db",
            'output_dir': "output",
            'new_base_path': "",
            'log_level': "INFO",
            'log_file': "excel_processor.log",
            
            # Phase-specific configurations
            'phase1': {
                'enabled': True,
                'save_identification_json': True,
                'identification_file': "workbook_identification.json"
            },
            'phase2': {
                'enabled': True,
                'recreate_db': True,
                'store_tabular_data': True
            },
            'phase3': {
                'enabled': True,
                'include_links_sheet': True,
                'fix_external_references': True
            },
            'phase4': {
                'enabled': True,
                'target_font_color': "FF000000"  # Black in ARGB format
            }
        }
        
        # Load configuration from file if provided
        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)
        
        # Override with environment variables
        self._load_from_environment()
        
        # Parse command-line arguments
        self._parse_command_line_args()
        
    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from a file (JSON, INI, or YAML)."""
        file_ext = os.path.splitext(config_file)[1].lower()
        
        try:
            if file_ext == '.json':
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    self._update_config(file_config)
            elif file_ext in ['.ini', '.cfg']:
                parser = configparser.ConfigParser()
                parser.read(config_file)
                
                # Convert ConfigParser to dict
                file_config = {}
                for section in parser.sections():
                    file_config[section] = {}
                    for key, value in parser.items(section):
                        # Try to parse lists and sets
                        if value.startswith('[') and value.endswith(']'):
                            file_config[section][key] = json.loads(value)
                        elif value.startswith('{') and value.endswith('}'):
                            file_config[section][key] = set(json.loads(value))
                        else:
                            file_config[section][key] = value
                
                self._update_config(file_config)
            elif file_ext in ['.yaml', '.yml']:
                try:
                    import yaml
                    with open(config_file, 'r') as f:
                        file_config = yaml.safe_load(f)
                        self._update_config(file_config)
                except ImportError:
                    print("PyYAML is not installed. Cannot parse YAML config file.")
            else:
                print(f"Unsupported configuration file format: {file_ext}")
        except Exception as e:
            print(f"Error loading configuration from file: {e}")
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Map environment variable names to config keys
        env_mapping = {
            'EXCEL_PROCESSOR_FILES': ('excel_files', lambda x: x.split(',')),
            'EXCEL_PROCESSOR_REPORT_SHEETS': ('report_sheets', lambda x: set(x.split(','))),
            'EXCEL_PROCESSOR_EXCLUDE_SHEETS': ('exclude_sheets', lambda x: set(x.split(','))),
            'EXCEL_PROCESSOR_DB_FILENAME': ('db_filename', str),
            'EXCEL_PROCESSOR_OUTPUT_DIR': ('output_dir', str),
            'EXCEL_PROCESSOR_NEW_BASE_PATH': ('new_base_path', str),
            'EXCEL_PROCESSOR_LOG_LEVEL': ('log_level', str),
            'EXCEL_PROCESSOR_LOG_FILE': ('log_file', str),
            'EXCEL_PROCESSOR_PHASE1_ENABLED': ('phase1.enabled', lambda x: x.lower() == 'true'),
            'EXCEL_PROCESSOR_PHASE2_ENABLED': ('phase2.enabled', lambda x: x.lower() == 'true'),
            'EXCEL_PROCESSOR_PHASE3_ENABLED': ('phase3.enabled', lambda x: x.lower() == 'true'),
            'EXCEL_PROCESSOR_PHASE4_ENABLED': ('phase4.enabled', lambda x: x.lower() == 'true'),
        }
        
        for env_var, (config_key, transform) in env_mapping.items():
            if env_var in os.environ:
                value = transform(os.environ[env_var])
                
                # Handle nested keys
                if '.' in config_key:
                    main_key, sub_key = config_key.split('.')
                    if main_key not in self.config:
                        self.config[main_key] = {}
                    self.config[main_key][sub_key] = value
                else:
                    self.config[config_key] = value
    
    def _parse_command_line_args(self) -> None:
        """Parse command-line arguments and update configuration."""
        parser = argparse.ArgumentParser(description='Excel Processing System')
        
        # General options
        parser.add_argument('--config', type=str, help='Path to configuration file')
        parser.add_argument('--excel-files', type=str, help='Comma-separated list of Excel files to process')
        parser.add_argument('--output-dir', type=str, help='Output directory for processed files')
        parser.add_argument('--db-filename', type=str, help='SQLite database filename')
        parser.add_argument('--new-base-path', type=str, help='New base path for external references')
        parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                           help='Logging level')
        
        # Phase-specific options
        parser.add_argument('--skip-phase1', action='store_true', help='Skip data identification phase')
        parser.add_argument('--skip-phase2', action='store_true', help='Skip data storage phase')
        parser.add_argument('--skip-phase3', action='store_true', help='Skip data recreation phase')
        parser.add_argument('--skip-phase4', action='store_true', help='Skip font color correction phase')
        
        args = parser.parse_args()
        
        # Update configuration from command-line arguments
        if args.config:
            self._load_from_file(args.config)
        
        if args.excel_files:
            self.config['excel_files'] = args.excel_files.split(',')
        
        if args.output_dir:
            self.config['output_dir'] = args.output_dir
        
        if args.db_filename:
            self.config['db_filename'] = args.db_filename
        
        if args.new_base_path:
            self.config['new_base_path'] = args.new_base_path
        
        if args.log_level:
            self.config['log_level'] = args.log_level
        
        # Update phase enable flags
        if args.skip_phase1:
            self.config['phase1']['enabled'] = False
        
        if args.skip_phase2:
            self.config['phase2']['enabled'] = False
        
        if args.skip_phase3:
            self.config['phase3']['enabled'] = False
        
        if args.skip_phase4:
            self.config['phase4']['enabled'] = False
    
    def _update_config(self, new_config: Dict[str, Any]) -> None:
        """Update configuration with new values, handling nested dictionaries."""
        for key, value in new_config.items():
            if isinstance(value, dict) and key in self.config and isinstance(self.config[key], dict):
                # Update nested dictionaries
                self.config[key].update(value)
            else:
                # Replace non-dict or new dict values
                self.config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key, with optional default."""
        if '.' in key:
            # Handle nested keys
            main_key, sub_key = key.split('.')
            if main_key in self.config and isinstance(self.config[main_key], dict):
                return self.config[main_key].get(sub_key, default)
            return default
        
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        if '.' in key:
            # Handle nested keys
            main_key, sub_key = key.split('.')
            if main_key not in self.config:
                self.config[main_key] = {}
            self.config[main_key][sub_key] = value
        else:
            self.config[key] = value
    
    def as_dict(self) -> Dict[str, Any]:
        """Return the entire configuration as a dictionary."""
        return self.config

class DataIdentificationConfig:
    """Configuration for the Data Identification phase."""
    def __init__(self, config: ExcelProcessorConfig):
        # General settings
        self.excel_files = config.get('excel_files', [])
        self.report_sheets = config.get('report_sheets', set())
        self.exclude_sheets = config.get('exclude_sheets', set())
        
        # Phase-specific settings
        self.enabled = config.get('phase1.enabled', True)
        self.save_identification_json = config.get('phase1.save_identification_json', True)
        self.identification_file = config.get('phase1.identification_file', "workbook_identification.json")
        
        # Advanced settings
        self.parse_formulas = config.get('phase1.parse_formulas', True)
        self.detect_references = config.get('phase1.detect_references', True)
        self.extract_metadata = config.get('phase1.extract_metadata', True)


class DataStorageConfig:
    """Configuration for the Data Storage phase."""
    def __init__(self, config: ExcelProcessorConfig):
        # General settings
        self.db_filename = config.get('db_filename', "excel_data.db")
        self.new_base_path = config.get('new_base_path', "")
        
        # Phase-specific settings
        self.enabled = config.get('phase2.enabled', True)
        self.recreate_db = config.get('phase2.recreate_db', True)
        self.store_tabular_data = config.get('phase2.store_tabular_data', True)
        
        # Advanced settings
        self.batch_size = config.get('phase2.batch_size', 1000)
        self.use_transactions = config.get('phase2.use_transactions', True)
        self.fix_external_references = config.get('phase2.fix_external_references', True)


class DataRecreationConfig:
    """Configuration for the Data Recreation phase."""
    def __init__(self, config: ExcelProcessorConfig):
        # General settings
        self.output_dir = config.get('output_dir', "output")
        self.new_base_path = config.get('new_base_path', "")
        
        # Phase-specific settings
        self.enabled = config.get('phase3.enabled', True)
        self.include_links_sheet = config.get('phase3.include_links_sheet', True)
        self.fix_external_references = config.get('phase3.fix_external_references', True)
        
        # Advanced settings
        self.copy_formatting = config.get('phase3.copy_formatting', True)
        self.output_suffix = config.get('phase3.output_suffix', "_recreated")


class FontColorCorrectionConfig:
    """Configuration for the Font Color Correction phase."""
    def __init__(self, config: ExcelProcessorConfig):
        # General settings
        self.output_dir = config.get('output_dir', "output")
        
        # Phase-specific settings
        self.enabled = config.get('phase4.enabled', True)
        self.target_font_color = config.get('phase4.target_font_color', "FF000000")  # Black in ARGB format
        
        # Advanced settings
        self.output_suffix = config.get('phase4.output_suffix', "_fixed")
        self.preserve_conditional_formatting = config.get('phase4.preserve_conditional_formatting', True)
        