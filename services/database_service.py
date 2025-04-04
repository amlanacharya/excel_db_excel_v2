import os
import json
import sqlite3
import logging
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple, Union

from excel_db_excel_v2.models.workbook import Workbook
from excel_db_excel_v2.models.sheet import Sheet
from excel_db_excel_v2.models.cell import Cell


class DatabaseService:
    """
    Service for database operations.
    Handles all database-related functionality including schema management,
    data storage, and retrieval.
    Follows Single Responsibility and Dependency Inversion Principles.
    """
    
    def __init__(self, db_filename: Optional[str] = None):
        """
        Initialize the database service.
        
        Args:
            db_filename (str, optional): Path to the SQLite database file.
        """
        self.db_filename = db_filename
        self.connection = None
        self.cursor = None
        self.logger = logging.getLogger(__name__)
        
        # Transaction state
        self.in_transaction = False
    
    def connect(self, db_filename: Optional[str] = None) -> sqlite3.Connection:
        """
        Connect to the database.
        
        Args:
            db_filename (str, optional): Path to the SQLite database file.
                                        If provided, overrides the one set in constructor.
        
        Returns:
            sqlite3.Connection: The database connection
            
        Raises:
            Exception: If connection fails
        """
        if db_filename:
            self.db_filename = db_filename
            
        if not self.db_filename:
            raise ValueError("No database filename specified")
            
        try:
            self.connection = sqlite3.connect(self.db_filename)
            self.cursor = self.connection.cursor()
            return self.connection
        except Exception as e:
            error_msg = f"Failed to connect to database {self.db_filename}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def close(self) -> None:
        """
        Close the database connection.
        """
        if self.connection:
            # Commit any pending changes
            if self.in_transaction:
                self.logger.warning("Closing database with active transaction. Committing changes.")
                self.connection.commit()
                self.in_transaction = False
                
            self.connection.close()
            self.connection = None
            self.cursor = None
    
    def begin_transaction(self) -> None:
        """
        Begin a database transaction.
        """
        if self.connection and not self.in_transaction:
            self.in_transaction = True
            # SQLite begins transactions automatically
            self.logger.debug("Transaction started")
    
    def commit_transaction(self) -> None:
        """
        Commit the current transaction.
        """
        if self.connection and self.in_transaction:
            self.connection.commit()
            self.in_transaction = False
            self.logger.debug("Transaction committed")
    
    def rollback_transaction(self) -> None:
        """
        Rollback the current transaction.
        """
        if self.connection and self.in_transaction:
            self.connection.rollback()
            self.in_transaction = False
            self.logger.debug("Transaction rolled back")
    
    def create_schema(self) -> None:
        """
        Create the database schema including all necessary tables.
        
        Raises:
            Exception: If schema creation fails
        """
        if not self.connection:
            raise ValueError("No database connection")
            
        try:
            # Create workbooks table
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS workbooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                properties TEXT
            )
            """)
            
            # Create sheets table
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workbook_id INTEGER,
                sheet_name TEXT,
                sheet_type TEXT,
                max_row INTEGER,
                max_column INTEGER,
                merged_cells TEXT,
                column_dimensions TEXT,
                row_dimensions TEXT,
                FOREIGN KEY (workbook_id) REFERENCES workbooks (id),
                UNIQUE (workbook_id, sheet_name)
            )
            """)
            
            # Create cells table - simplified to only store value and formula status
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS cells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sheet_id INTEGER,
                coordinate TEXT,
                value TEXT,
                is_formula BOOLEAN,
                FOREIGN KEY (sheet_id) REFERENCES sheets (id),
                UNIQUE (sheet_id, coordinate)
            )
            """)
            
            # Create tabular_data table
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tabular_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workbook TEXT,
                sheet TEXT,
                table_name TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            self.connection.commit()
            self.logger.info("Database schema created successfully")
            
        except Exception as e:
            error_msg = f"Failed to create database schema: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def insert_workbook(self, workbook: Workbook) -> int:
        """
        Insert a workbook into the database.
        
        Args:
            workbook (Workbook): The workbook model to insert
            
        Returns:
            int: The ID of the inserted workbook
            
        Raises:
            Exception: If insertion fails
        """
        if not self.connection:
            raise ValueError("No database connection")
            
        try:
            # Convert properties to JSON
            properties_json = json.dumps(workbook.properties)
            
            # Insert workbook
            self.cursor.execute(
                "INSERT OR REPLACE INTO workbooks (filename, properties) VALUES (?, ?)",
                (workbook.filename, properties_json)
            )
            
            # Get workbook ID
            self.cursor.execute("SELECT id FROM workbooks WHERE filename = ?", (workbook.filename,))
            workbook_id = self.cursor.fetchone()[0]
            
            # Commit changes if not in a transaction
            if not self.in_transaction:
                self.connection.commit()
                
            return workbook_id
            
        except Exception as e:
            error_msg = f"Failed to insert workbook {workbook.filename}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def insert_sheet(self, workbook_id: int, sheet: Sheet) -> int:
        """
        Insert a sheet into the database.
        
        Args:
            workbook_id (int): The ID of the parent workbook
            sheet (Sheet): The sheet model to insert
            
        Returns:
            int: The ID of the inserted sheet
            
        Raises:
            Exception: If insertion fails
        """
        if not self.connection:
            raise ValueError("No database connection")
            
        try:
            # Convert dimensions and merged cells to JSON
            merged_cells_json = json.dumps(sheet.merged_cells)
            column_dimensions_json = json.dumps(sheet.column_dimensions)
            row_dimensions_json = json.dumps(sheet.row_dimensions)
            
            # Insert sheet
            self.cursor.execute(
                """INSERT OR REPLACE INTO sheets 
                   (workbook_id, sheet_name, sheet_type, max_row, max_column, merged_cells, column_dimensions, row_dimensions) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (workbook_id, sheet.name, sheet.sheet_type, sheet.max_row, sheet.max_column, 
                 merged_cells_json, column_dimensions_json, row_dimensions_json)
            )
            
            # Get sheet ID
            self.cursor.execute("SELECT id FROM sheets WHERE workbook_id = ? AND sheet_name = ?", 
                               (workbook_id, sheet.name))
            sheet_id = self.cursor.fetchone()[0]
            
            # Commit changes if not in a transaction
            if not self.in_transaction:
                self.connection.commit()
                
            return sheet_id
            
        except Exception as e:
            error_msg = f"Failed to insert sheet {sheet.name}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def insert_cell(self, sheet_id: int, cell: Cell) -> int:
        """
        Insert a cell into the database.
        
        Args:
            sheet_id (int): The ID of the parent sheet
            cell (Cell): The cell model to insert
            
        Returns:
            int: The ID of the inserted cell
            
        Raises:
            Exception: If insertion fails
        """
        if not self.connection:
            raise ValueError("No database connection")
            
        try:
            # Convert value to string for storage
            value = str(cell.value) if cell.value is not None else ""
            
            # Insert cell
            self.cursor.execute(
                "INSERT OR REPLACE INTO cells (sheet_id, coordinate, value, is_formula) VALUES (?, ?, ?, ?)",
                (sheet_id, cell.coordinate, value, cell.is_formula)
            )
            
            # Get cell ID
            self.cursor.execute("SELECT id FROM cells WHERE sheet_id = ? AND coordinate = ?", 
                               (sheet_id, cell.coordinate))
            cell_id = self.cursor.fetchone()[0]
            
            # Commit changes if not in a transaction
            if not self.in_transaction:
                self.connection.commit()
                
            return cell_id
            
        except Exception as e:
            error_msg = f"Failed to insert cell {cell.coordinate}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def store_sheet_as_table(self, workbook_filename: str, sheet_name: str, table_name: str) -> bool:
        """
        Store a sheet as a separate table in the database.
        
        Args:
            workbook_filename (str): The filename of the workbook
            sheet_name (str): The name of the sheet
            table_name (str): The name of the table to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connection:
            raise ValueError("No database connection")
            
        try:
            # Check if the file exists
            if not os.path.exists(workbook_filename):
                self.logger.warning(f"File not found: {workbook_filename}")
                return False
                
            # Read the sheet as a DataFrame
            df = pd.read_excel(workbook_filename, sheet_name=sheet_name)
            
            # Store the DataFrame in the database
            df.to_sql(table_name, self.connection, if_exists='replace', index=False)
            
            # Record this table in the tabular_data table
            self.cursor.execute(
                "INSERT OR REPLACE INTO tabular_data (workbook, sheet, table_name) VALUES (?, ?, ?)",
                (workbook_filename, sheet_name, table_name)
            )
            
            # Commit changes
            self.connection.commit()
            
            self.logger.info(f"Stored tabular data for sheet '{sheet_name}' in table '{table_name}'")
            return True
            
        except Exception as e:
            error_msg = f"Failed to store tabular data for sheet '{sheet_name}': {str(e)}"
            self.logger.error(error_msg)
            return False
    
    def get_workbooks(self) -> List[Workbook]:
        """
        Get all workbooks from the database.
        
        Returns:
            List[Workbook]: List of workbook models
            
        Raises:
            Exception: If retrieval fails
        """
        if not self.connection:
            raise ValueError("No database connection")
            
        try:
            # Get all workbooks
            self.cursor.execute("SELECT id, filename, properties FROM workbooks")
            workbook_rows = self.cursor.fetchall()
            
            workbooks = []
            for workbook_id, filename, properties_json in workbook_rows:
                # Convert JSON to dictionary
                properties = json.loads(properties_json)
                
                # Create workbook model
                workbook = Workbook(filename, properties)
                
                # Get sheets for this workbook
                self.cursor.execute("""
                    SELECT id, sheet_name, sheet_type, max_row, max_column, 
                           merged_cells, column_dimensions, row_dimensions
                    FROM sheets
                    WHERE workbook_id = ?
                """, (workbook_id,))
                sheet_rows = self.cursor.fetchall()
                
                for (sheet_id, sheet_name, sheet_type, max_row, max_column, 
                     merged_cells_json, column_dimensions_json, row_dimensions_json) in sheet_rows:
                    
                    # Convert JSON to objects
                    merged_cells = json.loads(merged_cells_json)
                    column_dimensions = json.loads(column_dimensions_json)
                    row_dimensions = json.loads(row_dimensions_json)
                    
                    # Create sheet model
                    sheet = Sheet(sheet_name, sheet_type, max_row, max_column)
                    sheet.merged_cells = merged_cells
                    sheet.column_dimensions = column_dimensions
                    sheet.row_dimensions = row_dimensions
                    
                    # Get cells for this sheet
                    self.cursor.execute("""
                        SELECT coordinate, value, is_formula
                        FROM cells
                        WHERE sheet_id = ?
                    """, (sheet_id,))
                    cell_rows = self.cursor.fetchall()
                    
                    for coordinate, value, is_formula in cell_rows:
                        # Create cell model
                        cell = Cell(coordinate, value, is_formula)
                        
                        # Add cell to sheet
                        sheet.add_cell(cell)
                    
                    # Add sheet to workbook
                    workbook.add_sheet(sheet)
                
                # Add workbook to list
                workbooks.append(workbook)
            
            return workbooks
            
        except Exception as e:
            error_msg = f"Failed to retrieve workbooks: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def get_sheet_by_name(self, workbook_filename: str, sheet_name: str) -> Optional[Sheet]:
        """
        Get a sheet by name from a specific workbook.
        
        Args:
            workbook_filename (str): The filename of the workbook
            sheet_name (str): The name of the sheet
            
        Returns:
            Optional[Sheet]: The sheet model if found, None otherwise
            
        Raises:
            Exception: If retrieval fails
        """
        if not self.connection:
            raise ValueError("No database connection")
            
        try:
            # Get workbook ID
            self.cursor.execute("SELECT id FROM workbooks WHERE filename = ?", (workbook_filename,))
            result = self.cursor.fetchone()
            
            if not result:
                self.logger.warning(f"Workbook {workbook_filename} not found")
                return None
                
            workbook_id = result[0]
            
            # Get sheet details
            self.cursor.execute("""
                SELECT id, sheet_type, max_row, max_column, merged_cells, column_dimensions, row_dimensions
                FROM sheets
                WHERE workbook_id = ? AND sheet_name = ?
            """, (workbook_id, sheet_name))
            result = self.cursor.fetchone()
            
            if not result:
                self.logger.warning(f"Sheet {sheet_name} not found in workbook {workbook_filename}")
                return None
                
            sheet_id, sheet_type, max_row, max_column, merged_cells_json, column_dimensions_json, row_dimensions_json = result
            
            # Convert JSON to objects
            merged_cells = json.loads(merged_cells_json)
            column_dimensions = json.loads(column_dimensions_json)
            row_dimensions = json.loads(row_dimensions_json)
            
            # Create sheet model
            sheet = Sheet(sheet_name, sheet_type, max_row, max_column)
            sheet.merged_cells = merged_cells
            sheet.column_dimensions = column_dimensions
            sheet.row_dimensions = row_dimensions
            
            # Get cells for this sheet
            self.cursor.execute("""
                SELECT coordinate, value, is_formula
                FROM cells
                WHERE sheet_id = ?
            """, (sheet_id,))
            cell_rows = self.cursor.fetchall()
            
            for coordinate, value, is_formula in cell_rows:
                # Create cell model
                cell = Cell(coordinate, value, is_formula)
                
                # Add cell to sheet
                sheet.add_cell(cell)
            
            return sheet
            
        except Exception as e:
            error_msg = f"Failed to retrieve sheet {sheet_name} from workbook {workbook_filename}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def get_available_tables(self) -> List[Dict[str, str]]:
        """
        Get a list of available tables stored as tabular data.
        
        Returns:
            List[Dict[str, str]]: List of dictionaries with table info
            
        Raises:
            Exception: If retrieval fails
        """
        if not self.connection:
            raise ValueError("No database connection")
            
        try:
            # Get all tables from tabular_data
            self.cursor.execute("""
                SELECT workbook, sheet, table_name, created_at
                FROM tabular_data
                ORDER BY workbook, sheet
            """)
            rows = self.cursor.fetchall()
            
            tables = []
            for workbook, sheet, table_name, created_at in rows:
                tables.append({
                    'workbook': workbook,
                    'sheet': sheet,
                    'table_name': table_name,
                    'created_at': created_at
                })
            
            return tables
            
        except Exception as e:
            error_msg = f"Failed to retrieve available tables: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Tuple]:
        """
        Execute a custom SQL query.
        
        Args:
            query (str): The SQL query to execute
            params (Tuple, optional): Parameters for the query
            
        Returns:
            List[Tuple]: List of result rows
            
        Raises:
            Exception: If query execution fails
        """
        if not self.connection:
            raise ValueError("No database connection")
            
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
                
            return self.cursor.fetchall()
            
        except Exception as e:
            error_msg = f"Failed to execute query: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e