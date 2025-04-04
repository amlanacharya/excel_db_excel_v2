class Workbook:
    """
    Represents an Excel workbook with its properties and sheets.
    Follows Single Responsibility Principle by focusing on workbook data.
    """
    def __init__(self, filename, properties=None):
        self.filename = filename
        self.properties = properties or {}
        self.sheets = {}  # Dictionary of Sheet objects
    
    def add_sheet(self, sheet):
        """Add a Sheet object to the workbook."""
        self.sheets[sheet.name] = sheet
    
    def get_sheet(self, sheet_name):
        """Get a Sheet object by name."""
        return self.sheets.get(sheet_name)
    
    def to_dict(self):
        """Convert the workbook to a dictionary representation."""
        return {
            'filename': self.filename,
            'properties': self.properties,
            'sheets': {name: sheet.to_dict() for name, sheet in self.sheets.items()}
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a Workbook object from a dictionary."""
        from .sheet import Sheet  # Import here to avoid circular imports
        
        workbook = cls(data['filename'], data['properties'])
        for name, sheet_data in data['sheets'].items():
            sheet = Sheet.from_dict(sheet_data)
            workbook.add_sheet(sheet)
        
        return workbook