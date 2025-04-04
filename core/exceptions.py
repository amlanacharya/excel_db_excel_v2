class ExcelProcessorError(Exception):
    """Base exception for all Excel Processor errors."""
    pass

class ConfigurationError(ExcelProcessorError):
    """Exception raised for configuration errors."""
    pass

class PhaseExecutionError(ExcelProcessorError):
    """Exception raised for errors during phase execution."""
    def __init__(self, phase_name, message, original_exception=None):
        self.phase_name = phase_name
        self.original_exception = original_exception
        super().__init__(f"Error in phase '{phase_name}': {message}")