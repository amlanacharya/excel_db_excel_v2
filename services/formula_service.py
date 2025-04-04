import os
import re
import logging
from typing import Dict, Any, Optional, List, Set, Tuple, Union


class FormulaService:
    """
    Service for formula handling and external references.
    Handles parsing, updating, and fixing formulas with external references.
    Follows Single Responsibility Principle.
    """
    def __init__(self, excel_files=None, new_base_path=""):
        """
        Initialize the formula service.
        
        Args:
            excel_files (List[str], optional): List of Excel file paths. Defaults to None.
            new_base_path (str, optional): New base path for external references. Defaults to "".
        """
        self.excel_files = excel_files or []
        self.new_base_path = new_base_path
        self.excel_file_map = self._create_excel_file_map()
        self.logger = logging.getLogger(__name__)
        
        # Define mapping for numeric index references
        self.index_to_filename = {
            '1': 'Deposits Data Lite.xlsx',
            '2': 'Loans Data Lite.xlsx',
            '3': 'Form X Report  Main Lite.xlsx'
        }
    
    def _create_excel_file_map(self) -> Dict[str, str]:
        """
        Create a mapping dictionary for Excel filenames with variations.
        
        Returns:
            Dict[str, str]: A dictionary mapping various forms of a filename to the original filename
        """
        excel_file_map = {}
        for file in self.excel_files:
            base_name = os.path.basename(file)
            name_without_ext = os.path.splitext(base_name)[0]
            clean_name = base_name.replace(" ", "")
            clean_name_without_ext = name_without_ext.replace(" ", "")
            
            # Add all variations to the map
            for key in [base_name, name_without_ext, clean_name, clean_name_without_ext]:
                excel_file_map[key.lower()] = base_name
        return excel_file_map
    
    def fix_external_references(self, formula: str) -> str:
        """
        Fix external references in Excel formulas by updating paths and reference formats.
        
        Args:
            formula (str): The formula to fix
            
        Returns:
            str: The updated formula with fixed external references
        """
        if not formula or not isinstance(formula, str):
            return formula
        
        # Log the formula for debugging if it has potential external references
        if "xlsx" in formula or ("[" in formula and "]" in formula):
            self.logger.debug(f"Analyzing formula with potential external reference: {formula}")
        
        # Define patterns to match different types of external references
        # Pattern to match standard external references like: 'Path\[Filename.xlsx]SheetName'!Range
        standard_pattern = r"'?([^']*\[([^]]+)\]([^!']*))'?!([A-Z0-9:$]+)"
        
        # Pattern to match references with numeric workbook indices like: [1]Deposits!L:L
        indexed_pattern = r"\[(\d+)\]([^!]+)!([A-Z0-9:$]+)"
        
        # Pattern to match non-conventional references that might include sheet names or file paths
        sheet_reference_pattern = r"([\w\s-]+\.xlsx)([\w\s-]+)"
        
        # Apply different patterns in sequence
        updated_formula = re.sub(standard_pattern, self._replace_standard_match, formula)
        updated_formula = re.sub(indexed_pattern, self._replace_indexed_match, updated_formula)
        updated_formula = re.sub(sheet_reference_pattern, self._replace_sheet_reference, updated_formula)
        
        # Debug output when formulas are changed
        if updated_formula != formula:
            self.logger.info(f"Formula updated:\nFrom: {formula}\nTo:   {updated_formula}")
            
        return updated_formula
    
    def _replace_standard_match(self, match) -> str:
        """
        Handle standard external references like 'Path\[Filename.xlsx]SheetName'!Range.
        
        Args:
            match: The regex match object
            
        Returns:
            str: The updated reference
        """
        full_path = match.group(1)  # The whole path with filename and sheet
        filename = match.group(2)   # Just the filename
        sheet = match.group(3)      # Just the sheet name
        cell_ref = match.group(4)   # The cell reference
        
        self.logger.debug(f"Found standard external reference - File: {filename}, Sheet: {sheet}, Cell: {cell_ref}")
        
        # Skip replacement if no new base path
        if not self.new_base_path:
            return match.group(0)
        
        # Check if this filename matches any of our known files (possibly with slight differences)
        target_filename = None
        for file_key, file_value in self.excel_file_map.items():
            # Case-insensitive comparison, ignore spaces and parentheses
            clean_filename = filename.lower().replace(" ", "").replace("(", "").replace(")", "")
            clean_key = file_key.lower().replace(" ", "").replace("(", "").replace(")", "")
            if clean_filename in clean_key or clean_key in clean_filename:
                target_filename = file_value
                break
        
        if target_filename:
            # Construct the new reference with the new path and matched filename
            new_ref = f"'{self.new_base_path}[{target_filename}]{sheet}'!{cell_ref}"
            self.logger.debug(f"Updated to: {new_ref}")
            return new_ref
        else:
            # If no match found, keep the original reference
            return match.group(0)
    
    def _replace_indexed_match(self, match) -> str:
        """
        Handle references with numeric workbook indices like [1]Deposits!L:L.
        
        Args:
            match: The regex match object
            
        Returns:
            str: The updated reference
        """
        workbook_index = match.group(1)  # The numeric index (e.g., '1')
        sheet_name = match.group(2)      # The sheet name (e.g., 'Deposits')
        cell_ref = match.group(3)        # The range reference (e.g., 'L:L')
        
        self.logger.debug(f"Found indexed external reference - Index: [{workbook_index}], Sheet: {sheet_name}, Cell: {cell_ref}")
        
        if workbook_index in self.index_to_filename and self.new_base_path:
            # For new base path, create a full path reference
            filename = self.index_to_filename[workbook_index]
            new_ref = f"'{self.new_base_path}[{filename}]{sheet_name}'!{cell_ref}"
            self.logger.debug(f"Mapped indexed reference to: {new_ref}")
            return new_ref
        else:
            # Keep the original indexed reference if no base path change or unknown index
            self.logger.debug(f"Preserving original indexed reference: [{workbook_index}]{sheet_name}!{cell_ref}")
            return match.group(0)
    
    def _replace_sheet_reference(self, match) -> str:
        """
        Handle non-conventional references that might include sheet names or file paths.
        
        Args:
            match: The regex match object
            
        Returns:
            str: The updated reference
        """
        file = match.group(1)
        sheet = match.group(2)
        self.logger.debug(f"Found non-standard reference - File: {file}, Content: {sheet}")
        
        # Skip replacement if no new base path
        if not self.new_base_path:
            return match.group(0)
        
        # Try to match with our known files
        target_filename = None
        for file_key, file_value in self.excel_file_map.items():
            clean_file = file.lower().replace(" ", "").replace("(", "").replace(")", "")
            clean_key = file_key.lower().replace(" ", "").replace("(", "").replace(")", "")
            if clean_file in clean_key or clean_key in clean_file:
                target_filename = file_value
                break
        
        if target_filename:
            return f"{self.new_base_path}{target_filename}{sheet}"
        return match.group(0)
    
    def detect_references(self, cell_value: Any) -> bool:
        """
        Detect if a cell value contains external references.
        
        Args:
            cell_value: The cell value to check
            
        Returns:
            bool: True if the value contains external references, False otherwise
        """
        if not isinstance(cell_value, str):
            return False
            
        # Check for indicators of external references
        return (
            '.xlsx' in cell_value or 
            '.xls' in cell_value or 
            ('[' in cell_value and ']' in cell_value)
        )
    
    def extract_references(self, formula: str) -> List[Dict[str, str]]:
        """
        Extract external references from a formula.
        
        Args:
            formula (str): The formula to analyze
            
        Returns:
            List[Dict[str, str]]: List of dictionaries containing reference details
        """
        if not formula or not isinstance(formula, str):
            return []
        
        references = []
        
        # Define patterns to match different types of external references
        standard_pattern = r"'?([^']*\[([^]]+)\]([^!']*))'?!([A-Z0-9:$]+)"
        indexed_pattern = r"\[(\d+)\]([^!]+)!([A-Z0-9:$]+)"
        
        # Find standard references
        for match in re.finditer(standard_pattern, formula):
            references.append({
                'type': 'standard',
                'full_path': match.group(1),
                'filename': match.group(2),
                'sheet': match.group(3),
                'cell_ref': match.group(4)
            })
        
        # Find indexed references
        for match in re.finditer(indexed_pattern, formula):
            workbook_index = match.group(1)
            filename = self.index_to_filename.get(workbook_index, f"Unknown[{workbook_index}]")
            
            references.append({
                'type': 'indexed',
                'index': workbook_index,
                'filename': filename,
                'sheet': match.group(2),
                'cell_ref': match.group(3)
            })
        
        return references