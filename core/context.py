import datetime
class ProcessingContext:
    """
    Context object to manage the state of the Excel processing pipeline.
    Follows the Dependency Inversion Principle by providing abstractions.
    """
    def __init__(self, config):
        # Configuration
        self.excel_files = config.get('excel_files', [])
        self.report_sheets = set(config.get('report_sheets', set()))
        self.exclude_sheets = set(config.get('exclude_sheets', set()))
        self.db_filename = config.get('db_filename', 'excel_data.db')
        self.output_dir = config.get('output_dir', 'output')
        self.new_base_path = config.get('new_base_path', '')
        
        # Runtime state
        self.workbook_data = {}
        self.excel_file_map = {}
        self.db_connection = None
        self.recreated_files = []
        self.fixed_files = []
        
        # Phase completion flags
        self.phases_completed = {
            'configuration': False,
            'data_identification': False,
            'data_storage': False,
            'data_recreation': False,
            'font_color_correction': False
        }
        
        # Performance metrics
        self.phase_timings = {}
        self.start_time = None
        self.end_time = None
        
        # Error handling
        self.errors = []
        self.warnings = []
        
    def mark_phase_complete(self, phase_name, timing=None):
        """Mark a phase as complete and record timing."""
        self.phases_completed[phase_name] = True
        if timing:
            self.phase_timings[phase_name] = timing
    
    def add_error(self, phase, message, exception=None):
        """Add an error to the context."""
        self.errors.append({
            'phase': phase,
            'message': message,
            'exception': str(exception) if exception else None,
            'timestamp': datetime.now()
        })
    
    def add_warning(self, phase, message):
        """Add a warning to the context."""
        self.warnings.append({
            'phase': phase,
            'message': message,
            'timestamp': datetime.now()
        })
    
    def validate_state_for_phase(self, phase_name):
        """Check if the state is valid for starting a phase."""
        if phase_name == 'data_identification':
            return len(self.excel_files) > 0 and self.phases_completed['configuration']
        elif phase_name == 'data_storage':
            return self.phases_completed['data_identification']
        elif phase_name == 'data_recreation':
            return self.phases_completed['data_storage']
        elif phase_name == 'font_color_correction':
            return self.phases_completed['data_recreation'] and len(self.recreated_files) > 0
        return True
    
    def get_status_report(self):
        """Generate a status report of the processing."""
        return {
            'phases_completed': self.phases_completed,
            'timings': self.phase_timings,
            'total_time': (self.end_time - self.start_time).total_seconds() if self.end_time else None,
            'errors': len(self.errors),
            'warnings': len(self.warnings),
            'files_processed': len(self.excel_files),
            'files_recreated': len(self.recreated_files),
            'files_fixed': len(self.fixed_files)
        }