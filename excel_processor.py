#!/usr/bin/env python3
"""
Excel Processing System
A modular system for processing Excel workbooks with formula and formatting preservation.

This tool handles the following operations:
1. Data Identification - Extract data from Excel files
2. Data Storage - Store extracted data in a SQLite database
3. Data Recreation - Recreate Excel files from stored data
4. Font Color Correction - Fix font colors in recreated files

Usage:
    python excel_processor.py [options]

Options:
    --config FILE           Path to configuration file (JSON, INI, or YAML)
    --excel-files FILES     Comma-separated list of Excel files to process
    --output-dir DIR        Output directory for processed files
    --db-filename FILE      SQLite database filename
    --new-base-path PATH    New base path for external references
    --log-level LEVEL       Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    --skip-phase1           Skip data identification phase
    --skip-phase2           Skip data storage phase
    --skip-phase3           Skip data recreation phase
    --skip-phase4           Skip font color correction phase
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Set, Tuple

from excel_db_excel_v2.config.config_manager import ExcelProcessorConfig
from excel_db_excel_v2.core.context import ProcessingContext
from excel_db_excel_v2.phases.phase1_identification import DataIdentificationPhase
from excel_db_excel_v2.phases.phase2_storage import DataStoragePhase
from excel_db_excel_v2.phases.phase3_recreation import DataRecreationPhase
from excel_db_excel_v2.phases.phase4_correction import FontColorCorrectionPhase
from excel_db_excel_v2.services.database_service import DatabaseService
from excel_db_excel_v2.services.excel_service import ExcelService
from excel_db_excel_v2.services.formula_service import FormulaService


def setup_logging(config: ExcelProcessorConfig) -> logging.Logger:
    """Set up the logging system."""
    log_level = getattr(logging, config.get('log_level', 'INFO').upper())
    log_file = config.get('log_file')
    
    handlers = []
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # Set up file handler if log file specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    return logging.getLogger('excel_processor')


def run_processor(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the Excel processor.
    
    Args:
        config_file (str, optional): Path to configuration file
        
    Returns:
        Dict[str, Any]: Processing results
    """
    # Load configuration
    config = ExcelProcessorConfig(config_file)
    
    # Set up logging
    logger = setup_logging(config)
    logger.info("Starting Excel Processing System")
    logger.info(f"Configuration loaded from: {config_file if config_file else 'defaults'}")
    
    # Create processing context
    context = ProcessingContext(config)
    context.logger = logger
    context.start_time = datetime.now()
    
    # Initialize services
    formula_service = FormulaService(
        excel_files=config.get('excel_files', []),
        new_base_path=config.get('new_base_path', '')
    )
    
    database_service = DatabaseService(
        db_filename=config.get('db_filename', 'excel_data.db')
    )
    
    excel_service = ExcelService(
        formula_service=formula_service
    )
    
    try:
        # Mark configuration phase complete
        context.mark_phase_complete('configuration')
        
        # Phase 1: Data Identification
        if config.get('phase1.enabled', True):
            logger.info("Starting Phase 1: Data Identification")
            
            phase1_config = config.get('phase1', {})
            phase1 = DataIdentificationPhase(excel_service, config)
            
            if phase1.validate_prerequisites(context):
                start_time = datetime.now()
                phase1_success = phase1.execute(context)
                end_time = datetime.now()
                
                if phase1_success:
                    elapsed = (end_time - start_time).total_seconds()
                    context.mark_phase_complete('data_identification', elapsed)
                    logger.info(f"Phase 1 completed successfully in {elapsed:.2f} seconds")
                else:
                    logger.error("Phase 1 failed")
                    return get_results(context)
            else:
                logger.error("Phase 1 prerequisites not met")
                return get_results(context)
        else:
            logger.info("Phase 1 skipped by configuration")
        
        # Phase 2: Data Storage
        if config.get('phase2.enabled', True):
            logger.info("Starting Phase 2: Data Storage")
            
            phase2_config = config.get('phase2', {})
            phase2 = DataStoragePhase(database_service, formula_service, config)
            
            if phase2.validate_prerequisites(context):
                start_time = datetime.now()
                phase2_success = phase2.execute(context)
                end_time = datetime.now()
                
                if phase2_success:
                    elapsed = (end_time - start_time).total_seconds()
                    context.mark_phase_complete('data_storage', elapsed)
                    logger.info(f"Phase 2 completed successfully in {elapsed:.2f} seconds")
                else:
                    logger.error("Phase 2 failed")
                    return get_results(context)
            else:
                logger.error("Phase 2 prerequisites not met")
                return get_results(context)
        else:
            logger.info("Phase 2 skipped by configuration")
        
        # Phase 3: Data Recreation
        if config.get('phase3.enabled', True):
            logger.info("Starting Phase 3: Data Recreation")
            
            phase3_config = config.get('phase3', {})
            phase3 = DataRecreationPhase(database_service, excel_service, formula_service, config)
            
            if phase3.validate_prerequisites(context):
                start_time = datetime.now()
                phase3_success = phase3.execute(context)
                end_time = datetime.now()
                
                if phase3_success:
                    elapsed = (end_time - start_time).total_seconds()
                    context.mark_phase_complete('data_recreation', elapsed)
                    logger.info(f"Phase 3 completed successfully in {elapsed:.2f} seconds")
                else:
                    logger.error("Phase 3 failed")
                    return get_results(context)
            else:
                logger.error("Phase 3 prerequisites not met")
                return get_results(context)
        else:
            logger.info("Phase 3 skipped by configuration")
        
        # Phase 4: Font Color Correction
        if config.get('phase4.enabled', True):
            logger.info("Starting Phase 4: Font Color Correction")
            
            phase4_config = config.get('phase4', {})
            phase4 = FontColorCorrectionPhase(excel_service, config)
            
            if phase4.validate_prerequisites(context):
                start_time = datetime.now()
                phase4_success = phase4.execute(context)
                end_time = datetime.now()
                
                if phase4_success:
                    elapsed = (end_time - start_time).total_seconds()
                    context.mark_phase_complete('font_color_correction', elapsed)
                    logger.info(f"Phase 4 completed successfully in {elapsed:.2f} seconds")
                else:
                    logger.error("Phase 4 failed")
                    return get_results(context)
            else:
                logger.error("Phase 4 prerequisites not met")
                return get_results(context)
        else:
            logger.info("Phase 4 skipped by configuration")
        
        # Close database connection if still open
        if database_service.connection:
            database_service.close()
        
        # Record completion
        context.end_time = datetime.now()
        total_time = (context.end_time - context.start_time).total_seconds()
        logger.info(f"Excel Processing System completed successfully in {total_time:.2f} seconds")
        
        return get_results(context)
        
    except Exception as e:
        logger.error(f"Excel Processing System failed: {str(e)}", exc_info=True)
        context.add_error("system", "Unhandled exception", e)
        
        # Close database connection if still open
        if database_service.connection:
            database_service.close()
        
        # Record completion
        context.end_time = datetime.now()
        return get_results(context)


def get_results(context: ProcessingContext) -> Dict[str, Any]:
    """
    Get processing results from context.
    
    Args:
        context (ProcessingContext): The processing context
        
    Returns:
        Dict[str, Any]: Processing results
    """
    results = {
        'success': all(context.phases_completed.values()),
        'phases_completed': context.phases_completed,
        'timings': context.phase_timings,
        'errors': context.errors,
        'warnings': context.warnings,
        'files_processed': len(context.excel_files) if hasattr(context, 'excel_files') else 0,
        'files_recreated': len(context.recreated_files) if hasattr(context, 'recreated_files') else 0,
        'files_fixed': len(context.fixed_files) if hasattr(context, 'fixed_files') else 0
    }
    
    if context.start_time and context.end_time:
        results['total_time'] = (context.end_time - context.start_time).total_seconds()
    
    return results


def get_user_input(prompt: str, default: str = '') -> str:
    """
    Get user input with a default value.
    
    Args:
        prompt (str): The prompt to display
        default (str, optional): Default value to use if no input provided
        
    Returns:
        str: The user input or default value
    """
    if default:
        user_input = input(f"{prompt} [{default}]: ")
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ")


def interactive_mode(config: Optional[ExcelProcessorConfig] = None) -> Dict[str, Any]:
    """
    Run the processor in interactive mode.
    
    Args:
        config (ExcelProcessorConfig, optional): Initial configuration
        
    Returns:
        Dict[str, Any]: Processing results
    """
    if not config:
        config = ExcelProcessorConfig()
    
    print("\n" + "="*70)
    print("EXCEL PROCESSING SYSTEM - INTERACTIVE MODE")
    print("="*70)
    
    # Get Excel files
    excel_files_str = get_user_input(
        "Enter Excel files to process (comma-separated)",
        ",".join(config.get('excel_files', []))
    )
    excel_files = [f.strip() for f in excel_files_str.split(',') if f.strip()]
    config.set('excel_files', excel_files)
    
    # Get new base path
    new_base_path = get_user_input(
        "Enter new base path for external references (leave empty to keep original)",
        config.get('new_base_path', '')
    )
    config.set('new_base_path', new_base_path)
    
    # Get output directory
    output_dir = get_user_input(
        "Enter output directory for processed files",
        config.get('output_dir', 'output')
    )
    config.set('output_dir', output_dir)
    
    # Get database filename
    db_filename = get_user_input(
        "Enter SQLite database filename",
        config.get('db_filename', 'excel_data.db')
    )
    config.set('db_filename', db_filename)
    
    # Confirm phase execution
    for phase in ['phase1', 'phase2', 'phase3', 'phase4']:
        phase_name = phase.replace('phase', 'Phase ')
        enabled = config.get(f'{phase}.enabled', True)
        response = get_user_input(f"Execute {phase_name}? (y/n)", 'y' if enabled else 'n')
        config.set(f'{phase}.enabled', response.lower() == 'y')
    
    # Create directory if needed
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        except Exception as e:
            print(f"ERROR: Failed to create output directory: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # Run the processor
    print("\nStarting Excel Processing System...")
    return run_processor(config)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Excel Processing System")
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    
    args = parser.parse_args()
    
    try:
        if args.interactive:
            if args.config:
                config = ExcelProcessorConfig(args.config)
                results = interactive_mode(config)
            else:
                results = interactive_mode()
        else:
            results = run_processor(args.config)
        
        # Print summary
        print("\n" + "="*70)
        print("PROCESSING RESULTS")
        print("="*70)
        print(f"Success: {'Yes' if results['success'] else 'No'}")
        print(f"Phases completed: {sum(1 for phase in results['phases_completed'].values() if phase)}/{len(results['phases_completed'])}")
        print(f"Total time: {results.get('total_time', 0):.2f} seconds")
        print(f"Files processed: {results['files_processed']}")
        print(f"Files recreated: {results['files_recreated']}")
        print(f"Files fixed: {results['files_fixed']}")
        print(f"Errors: {len(results['errors'])}")
        print(f"Warnings: {len(results['warnings'])}")
        
        # Exit with appropriate code
        sys.exit(0 if results['success'] else 1)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()