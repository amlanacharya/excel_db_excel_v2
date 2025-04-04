"""
Default configuration values for the Excel Processing System.
"""

# General configuration defaults
EXCEL_FILES = ["Deposits Data Lite.xlsx", "Form X Report  Main Lite.xlsx", "Loans Data Lite.xlsx"]
REPORT_SHEETS = {"Part I", "Part II", "Part III", "MIS-Report"}
EXCLUDE_SHEETS = {"Pivot-Borrowings"}
DB_FILENAME = "excel_data.db"
OUTPUT_DIR = "output"
NEW_BASE_PATH = ""
LOG_LEVEL = "INFO"
LOG_FILE = "excel_processor.log"

# Phase 1: Data Identification defaults
PHASE1_DEFAULTS = {
    'enabled': True,
    'save_identification_json': True,
    'identification_file': "workbook_identification.json",
    'parse_formulas': True,
    'detect_references': True,
    'extract_metadata': True
}

# Phase 2: Data Storage defaults
PHASE2_DEFAULTS = {
    'enabled': True,
    'recreate_db': True,
    'store_tabular_data': True,
    'batch_size': 1000,
    'use_transactions': True,
    'fix_external_references': True
}

# Phase 3: Data Recreation defaults
PHASE3_DEFAULTS = {
    'enabled': True,
    'include_links_sheet': True,
    'fix_external_references': True,
    'copy_formatting': True,
    'output_suffix': "_recreated"
}

# Phase 4: Font Color Correction defaults
PHASE4_DEFAULTS = {
    'enabled': True,
    'target_font_color': "FF000000",  # Black in ARGB format
    'output_suffix': "_fixed",
    'preserve_conditional_formatting': True
}

# Compiled default configuration dictionary
DEFAULT_CONFIG = {
    'excel_files': EXCEL_FILES,
    'report_sheets': REPORT_SHEETS,
    'exclude_sheets': EXCLUDE_SHEETS,
    'db_filename': DB_FILENAME,
    'output_dir': OUTPUT_DIR,
    'new_base_path': NEW_BASE_PATH,
    'log_level': LOG_LEVEL,
    'log_file': LOG_FILE,
    'phase1': PHASE1_DEFAULTS,
    'phase2': PHASE2_DEFAULTS,
    'phase3': PHASE3_DEFAULTS,
    'phase4': PHASE4_DEFAULTS
}