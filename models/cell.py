class Cell:
    """
    Represents a cell with its value and formula status.
    Follows Single Responsibility Principle by focusing on cell data.
    """
    def __init__(self, coordinate, value=None, is_formula=False):
        self.coordinate = coordinate
        self.value = value
        self.is_formula = is_formula
    
    def to_dict(self):
        """Convert the cell to a dictionary representation."""
        return {
            'coordinate': self.coordinate,
            'value': self.value,
            'is_formula': self.is_formula
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a Cell object from a dictionary."""
        return cls(data['coordinate'], data['value'], data['is_formula'])