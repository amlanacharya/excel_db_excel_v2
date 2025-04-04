"""
Phase 2: Data Storage
Stores identified data in a SQLite database.
"""

import os
import json
from typing import Dict, Any, Optional, List, Set, Tuple

from excel_db_excel_v2.phases import Phase
from excel_db_excel_v2.models.workbook import Workbook
from excel_db_excel_v2.models.sheet import Sheet
from excel_db_excel_v2.models.cell import Cell
from excel_db_excel_v2.core.context import ProcessingContext
from excel_db_excel_v2.core.exceptions import PhaseExecutionError
from excel_db_excel_v2.services.database_service import DatabaseService
from excel_db_excel_v2.services.formula_service import FormulaService
from excel_db_excel_v2.services.excel_service import ExcelService



class DataStoragePhase(Phase):
    """
    Phase 2: Store identified data in SQLite database.
    Follows Single Responsibility Principle by focusing on just data storage.
    """
    def __init__(self, database_service: DatabaseService, formula_service: FormulaService, config: Any):
        self.database_service = database_service
        self.formula_service = formula_service
        self.config = config
        self.logger = None
        
    def validate_prerequisites(self, context: ProcessingContext) -> bool:
        """Validate that prerequisites for the phase are met."""
        self.logger = context.logger
        
        if not context.phases_completed.get("data_identification", False):
            self.logger.error("Data identification phase has not been completed")
            context.add_error("data_storage", "Data identification phase has not been completed")
            return False
            
        if not context.workbook_data:
            self.logger.error("No workbook data to store")
            context.add_error("data_storage", "No workbook data to store")
            return False
        
        return True
        
    def execute(self, context: ProcessingContext) -> bool:
        """Execute the data storage phase."""
        try:
            self.logger = context.logger
            self.logger.info("Starting Data Storage Phase")
            
            # Set up database
            if self.config.recreate_db and os.path.exists(self.config.db_filename):
                self.logger.info(f"Removing existing database: {self.config.db_filename}")
                try:
                    os.remove(self.config.db_filename)
                except PermissionError as e:
                    error_msg = f"Could not remove existing database. Make sure it's not in use by another program: {str(e)}"
                    self.logger.error(error_msg)
                    context.add_error("data_storage", error_msg, e)
                    return False
            
            # Connect to database and create schema
            self.logger.info(f"Setting up database: {self.config.db_filename}")
            try:
                self.database_service.connect(self.config.db_filename)
                self.database_service.create_schema()
            except Exception as e:
                error_msg = f"Failed to set up database: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                context.add_error("data_storage", error_msg, e)
                return False
            
            # Process each workbook from the context
            files_processed = 0
            for file, workbook_data in context.workbook_data.items():
                self.logger.info(f"Storing workbook: {file}")
                try:
                    workbook = Workbook.from_dict(workbook_data)
                    self._store_workbook(workbook, context)
                    files_processed += 1
                except Exception as e:
                    error_msg = f"Failed to store workbook {file}: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    context.add_error("data_storage", error_msg, e)
                    # Continue with other workbooks
            
            # Close database connection
            self.database_service.close()
            
            if files_processed == 0:
                self.logger.warning("No workbooks were successfully stored")
                context.add_warning("data_storage", "No workbooks were successfully stored")
                return False
                
            context.mark_phase_complete("data_storage")
            self.logger.info(f"Data Storage Phase completed successfully - {files_processed} workbooks stored")
            return True
            
        except Exception as e:
            self.logger.error(f"Data Storage Phase failed: {str(e)}", exc_info=True)
            context.add_error("data_storage", "Failed to store data", e)
            if self.database_service.connection:
                self.database_service.close()
            raise PhaseExecutionError("data_storage", str(e), e)
    
    def _store_workbook(self, workbook: Workbook, context: ProcessingContext) -> None:
        """
        Store a workbook in the database.
        
        Args:
            workbook: The workbook to store
            context: The processing context
        """
        # Store the workbook
        workbook_id = self.database_service.insert_workbook(workbook)
        
        # Store each sheet
        for sheet_name, sheet in workbook.sheets.items():
            self.logger.info(f"Storing sheet: {sheet_name}")
            sheet_id = self.database_service.insert_sheet(workbook_id, sheet)
            
            # Store each cell
            batch_size = self.config.batch_size
            cell_batch = []
            total_cells = len(sheet.cells)
            processed_cells = 0
            
            for coordinate, cell in sheet.cells.items():
                # Fix external references if enabled
                if self.config.fix_external_references and cell.is_formula:
                    original_value = cell.value
                    cell.value = self.formula_service.fix_external_references(cell.value)
                    if cell.value != original_value:
                        self.logger.debug(f"Updated formula in {sheet_name}!{coordinate}: {original_value} -> {cell.value}")
                
                # Add cell to batch
                cell_batch.append((sheet_id, cell))
                processed_cells += 1
                
                # Process batch if batch size reached or this is the last cell
                if len(cell_batch) >= batch_size or processed_cells == total_cells:
                    if self.config.use_transactions:
                        self.database_service.begin_transaction()
                        
                    try:
                        for s_id, c in cell_batch:
                            self.database_service.insert_cell(s_id, c)
                            
                        if self.config.use_transactions:
                            self.database_service.commit_transaction()
                    except Exception as e:
                        if self.config.use_transactions:
                            self.database_service.rollback_transaction()
                        error_msg = f"Failed to insert cell batch in {sheet_name}: {str(e)}"
                        self.logger.error(error_msg)
                        context.add_error("data_storage", error_msg, e)
                        raise
                    
                    cell_batch = []
                    self.logger.debug(f"Processed {processed_cells}/{total_cells} cells in {sheet_name}")
            
            # Store as tabular data if enabled and this is a non-report sheet
            if self.config.store_tabular_data and sheet.sheet_type == "non_report":
                self._store_as_tabular_data(workbook, sheet, context)
    
    def _store_as_tabular_data(self, workbook: Workbook, sheet: Sheet, context: ProcessingContext) -> None:
        """
        Store a sheet as tabular data in the database.
        
        Args:
            workbook: The workbook containing the sheet
            sheet: The sheet to store as tabular data
            context: The processing context
        """
        try:
            base_name = os.path.splitext(workbook.filename)[0]
            table_name = f"{base_name}_{sheet.name}".replace(" ", "_").replace("-", "_")
            
            self.logger.info(f"Storing tabular data for sheet '{sheet.name}' in table '{table_name}'")
            self.database_service.store_sheet_as_table(workbook.filename, sheet.name, table_name)
            
        except Exception as e:
            error_msg = f"Failed to store tabular data for sheet '{sheet.name}': {str(e)}"
            self.logger.warning(error_msg)
            context.add_warning("data_storage", error_msg)
            # Continue execution - this is not critical