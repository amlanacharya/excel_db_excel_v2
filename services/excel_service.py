import os
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from copy import copy

import openpyxl
from openpyxl.workbook.workbook import Workbook as OpenpyxlWorkbook
from openpyxl.worksheet.worksheet import Worksheet as OpenpyxlWorksheet

from excel_db_excel_v2.models.workbook import Workbook
from excel_db_excel_v2.models.sheet import Sheet
from excel_db_excel_v2.models.cell import Cell
from excel_db_excel_v2.services.formula_service import FormulaService


class ExcelService:
    """
    Service for Excel file operations.
    Handles reading from Excel files, creating workbook models, and saving Excel files.
    Follows Single Responsibility and Dependency Inversion Principles.
    """
    
    def __init__(self, formula_service=None):
        """
        Initialize the Excel service.
        
        Args:
            formula_service (FormulaService, optional): Service for handling formulas. If None, 
                                                       a new instance will be created.
        """
        self.formula_service = formula_service or FormulaService()
        self.logger = logging.getLogger(__name__)
    
    def load_workbook(self, filename: str, data_only: bool = False) -> Workbook:
        """
        Load an Excel workbook and convert it to our Workbook model.
        
        Args:
            filename (str): Path to the Excel file
            data_only (bool): Whether to load values instead of formulas
            
        Returns:
            Workbook: Our workbook model
            
        Raises:
            ValueError: If the file doesn't exist or isn't a valid Excel file
        """
        if not os.path.exists(filename):
            raise ValueError(f"File not found: {filename}")
            
        try:
            openpyxl_wb = openpyxl.load_workbook(filename, data_only=data_only)
        except Exception as e:
            raise ValueError(f"Failed to load workbook {filename}: {str(e)}")
        
        # Extract metadata
        properties = self.extract_workbook_metadata(openpyxl_wb)
        
        # Create workbook model
        workbook = Workbook(
            filename=os.path.basename(filename),
            properties=properties
        )
        
        # Process each sheet
        for sheet_name in openpyxl_wb.sheetnames:
            ws = openpyxl_wb[sheet_name]
            
            # Create the sheet model
            sheet = Sheet(
                name=sheet_name,
                sheet_type="unknown",  # Will be determined by caller
                max_row=ws.max_row,
                max_column=ws.max_column
            )
            
            # Add merged cells
            sheet.merged_cells = [str(merged_range) for merged_range in ws.merged_cells.ranges]
            
            # Add column dimensions
            sheet.column_dimensions = {
                col: {"width": ws.column_dimensions[col].width} 
                for col in ws.column_dimensions
            }
            
            # Add row dimensions
            sheet.row_dimensions = {
                str(row): {"height": ws.row_dimensions[row].height} 
                for row in ws.row_dimensions
            }
            
            # Process all cells
            for row in range(1, ws.max_row + 1):
                for col in range(1, ws.max_column + 1):
                    openpyxl_cell = ws.cell(row=row, column=col)
                    
                    # Skip empty cells
                    if openpyxl_cell.value is None:
                        continue
                    
                    # Create cell model
                    coordinate = openpyxl_cell.coordinate
                    
                    # Determine if the cell contains a formula
                    is_formula = (isinstance(openpyxl_cell.value, str) and 
                                 openpyxl_cell.value.startswith('='))
                    
                    # Create cell
                    cell = Cell(
                        coordinate=coordinate,
                        value=openpyxl_cell.value,
                        is_formula=is_formula
                    )
                    
                    sheet.add_cell(cell)
            
            # Add the sheet to the workbook
            workbook.add_sheet(sheet)
        
        return workbook
    
    def save_workbook(self, workbook: Workbook, output_file: str) -> bool:
        """
        Create an Excel workbook from our Workbook model and save it.
        
        Args:
            workbook (Workbook): The workbook model to save
            output_file (str): Path where the Excel file should be saved
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            Exception: If there's an error saving the workbook
        """
        # Create a new openpyxl workbook
        openpyxl_wb = OpenpyxlWorkbook()
        
        # Remove the default sheet if necessary
        if len(workbook.sheets) > 0:
            default_sheet = openpyxl_wb.active
            openpyxl_wb.remove(default_sheet)
        
        # Process each sheet
        for sheet_name, sheet in workbook.sheets.items():
            # Create the sheet
            ws = openpyxl_wb.create_sheet(title=sheet_name)
            
            # Apply merged cells
            for merged_range in sheet.merged_cells:
                ws.merge_cells(merged_range)
            
            # Apply column dimensions
            for col_key, properties in sheet.column_dimensions.items():
                if col_key in ws.column_dimensions and properties.get("width"):
                    ws.column_dimensions[col_key].width = properties["width"]
            
            # Apply row dimensions
            for row_key, properties in sheet.row_dimensions.items():
                try:
                    row = int(row_key)
                    if row in ws.row_dimensions and properties.get("height"):
                        ws.row_dimensions[row].height = properties["height"]
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid row key: {row_key}")
            
            # Populate cells
            for coordinate, cell in sheet.cells.items():
                self._set_cell_value(ws, coordinate, cell, sheet_name)
        
        # Save the workbook
        try:
            openpyxl_wb.save(output_file)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save workbook to {output_file}: {str(e)}")
            raise
    
    def extract_workbook_metadata(self, openpyxl_wb: OpenpyxlWorkbook) -> Dict[str, Any]:
        """
        Extract metadata from an openpyxl workbook.
        
        Args:
            openpyxl_wb (OpenpyxlWorkbook): The openpyxl workbook
            
        Returns:
            Dict[str, Any]: Dictionary with workbook metadata
        """
        properties = {
            'title': openpyxl_wb.properties.title,
            'creator': openpyxl_wb.properties.creator,
            'created': str(openpyxl_wb.properties.created) if openpyxl_wb.properties.created else None,
            'sheet_names': openpyxl_wb.sheetnames
        }
        
        # Add more metadata if available
        if hasattr(openpyxl_wb.properties, 'modified'):
            properties['modified'] = str(openpyxl_wb.properties.modified) if openpyxl_wb.properties.modified else None
            
        if hasattr(openpyxl_wb.properties, 'lastModifiedBy'):
            properties['last_modified_by'] = openpyxl_wb.properties.lastModifiedBy
            
        return properties
    
    def copy_cell_formatting(self, source_cell, target_cell) -> bool:
        """
        Copy formatting from source cell to target cell.
        
        Args:
            source_cell: The openpyxl source cell
            target_cell: The openpyxl target cell
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Copy font properties
            target_cell.font = copy(source_cell.font)
            
            # Copy fill properties
            target_cell.fill = copy(source_cell.fill)
            
            # Copy border properties
            target_cell.border = copy(source_cell.border)
            
            # Copy number format
            target_cell.number_format = source_cell.number_format
            
            # Copy protection
            if source_cell.protection:
                target_cell.protection = copy(source_cell.protection)
            
            # Copy alignment
            target_cell.alignment = copy(source_cell.alignment)
            return True
            
        except Exception as e:
            self.logger.error(f"Error copying formatting from {source_cell.coordinate}: {e}")
            return False
    
    def update_external_links(self, openpyxl_wb: OpenpyxlWorkbook, new_base_path: str) -> Dict[str, int]:
        """
        Update external links in formulas across the workbook.
        
        Args:
            openpyxl_wb (OpenpyxlWorkbook): The openpyxl workbook
            new_base_path (str): The new base path for external references
            
        Returns:
            Dict[str, int]: Count of updates per sheet
        """
        if not new_base_path:
            return {}
            
        result = {}
        
        # Process each sheet
        for sheet_name in openpyxl_wb.sheetnames:
            ws = openpyxl_wb[sheet_name]
            updates_count = 0
            
            # Check cells for formulas
            for row in range(1, ws.max_row + 1):
                for col in range(1, ws.max_column + 1):
                    cell = ws.cell(row=row, column=col)
                    
                    # Skip cells without formulas
                    if not cell.value or not isinstance(cell.value, str) or not cell.value.startswith('='):
                        continue
                    
                    # Fix external references in formula
                    original_formula = cell.value
                    updated_formula = self.formula_service.fix_external_references(original_formula)
                    
                    if updated_formula != original_formula:
                        cell.value = updated_formula
                        updates_count += 1
            
            if updates_count > 0:
                result[sheet_name] = updates_count
        
        return result
    
    def _set_cell_value(self, worksheet: OpenpyxlWorksheet, coordinate: str, 
                        cell: Cell, sheet_name: str) -> None:
        """
        Set the value of a cell in the worksheet.
        
        Args:
            worksheet (OpenpyxlWorksheet): The openpyxl worksheet
            coordinate (str): The cell coordinate
            cell (Cell): The cell model
            sheet_name (str): The name of the sheet (for logging)
        """
        try:
            if cell.is_formula:
                # Handle formula cells
                formula_value = cell.value
                
                # Special handling for indexed references in specific sheets
                is_special_sheet = sheet_name in ["MIS-Report", "Part I", "Part II", "Part III"]
                has_indexed_ref = ('[1]' in formula_value) or ('[2]' in formula_value) or ('[3]' in formula_value)
                
                try:
                    if is_special_sheet and has_indexed_ref:
                        # For indexed references, set value directly
                        worksheet[coordinate].value = formula_value
                    elif formula_value.startswith('='):
                        # Standard formula
                        worksheet[coordinate].value = None
                        worksheet[coordinate].formula = formula_value[1:]
                    else:
                        # Non-standard formula
                        worksheet[coordinate].value = None
                        worksheet[coordinate].formula = formula_value
                except Exception as e:
                    self.logger.warning(f"Error setting formula in {sheet_name}!{coordinate}: {e}")
                    worksheet[coordinate].value = formula_value
            else:
                # Handle non-formula cells
                value = cell.value
                
                # Convert value to appropriate type
                if isinstance(value, str):
                    if value.lower() == 'true':
                        worksheet[coordinate] = True
                    elif value.lower() == 'false':
                        worksheet[coordinate] = False
                    else:
                        try:
                            if value.isdigit():
                                worksheet[coordinate] = int(value)
                            else:
                                try:
                                    worksheet[coordinate] = float(value)
                                except ValueError:
                                    worksheet[coordinate] = value
                        except (ValueError, TypeError, AttributeError):
                            worksheet[coordinate] = value
                else:
                    worksheet[coordinate] = value
                
        except Exception as e:
            self.logger.warning(f"Error setting value in {sheet_name}!{coordinate}: {e}")
            try:
                # Fallback to setting as string
                worksheet[coordinate] = str(cell.value)
            except Exception:
                self.logger.error(f"Failed to set value in {sheet_name}!{coordinate} even as string")