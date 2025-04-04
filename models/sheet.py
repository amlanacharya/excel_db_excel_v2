class Sheet:
    """
    Represents a worksheet with its properties and cells.
    Follows Single Responsibility Principle by focusing on sheet data.
    """
    def __init__(self, name, sheet_type, max_row=0, max_column=0):
        self.name = name
        self.sheet_type = sheet_type  # 'report' or 'non_report'
        self.max_row = max_row
        self.max_column = max_column
        self.merged_cells = []
        self.column_dimensions = {}
        self.row_dimensions = {}
        self.cells = {}  # Dictionary of Cell objects
    
    def add_cell(self, cell):
        """Add a Cell object to the sheet."""
        self.cells[cell.coordinate] = cell
    
    def get_cell(self, coordinate):
        """Get a Cell object by coordinate."""
        return self.cells.get(coordinate)
    
    def to_dict(self):
        """Convert the sheet to a dictionary representation."""
        return {
            'name': self.name,
            'type': self.sheet_type,
            'max_row': self.max_row,
            'max_column': self.max_column,
            'merged_cells': self.merged_cells,
            'column_dimensions': self.column_dimensions,
            'row_dimensions': self.row_dimensions,
            'cells': {coord: cell.to_dict() for coord, cell in self.cells.items()}
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a Sheet object from a dictionary."""
        from .cell import Cell  # Import here to avoid circular imports
        
        sheet = cls(data['name'], data['type'], data['max_row'], data['max_column'])
        sheet.merged_cells = data['merged_cells']
        sheet.column_dimensions = data['column_dimensions']
        sheet.row_dimensions = data['row_dimensions']
        
        for coord, cell_data in data['cells'].items():
            cell = Cell.from_dict(cell_data)
            sheet.add_cell(cell)
        
        return sheet