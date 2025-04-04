class DatabaseService:
    """
    Service for database operations.
    Follows Single Responsibility and Dependency Inversion Principles.
    """
    def __init__(self, db_filename):
        self.db_filename = db_filename
        self.connection = None
    
    def connect(self):
        """Connect to the database."""
        self.connection = sqlite3.connect(self.db_filename)
        return self.connection
    
    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def create_schema(self):
        """Create the database schema."""
        # Implementation as in the original script
        pass
    
    def insert_workbook(self, workbook):
        """Insert a workbook into the database."""
        # Implementation using the Workbook model
        pass
    
    def insert_sheet(self, workbook_id, sheet):
        """Insert a sheet into the database."""
        # Implementation using the Sheet model
        pass
    
    def insert_cell(self, sheet_id, cell):
        """Insert a cell into the database."""
        # Implementation using the Cell model
        pass
    
    def get_workbooks(self):
        """Get all workbooks from the database."""
        # Implementation returning Workbook models
        pass