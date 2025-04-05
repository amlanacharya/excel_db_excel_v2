import os
import json
from datetime import datetime, date

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

def serialize_to_json(data, file_path):
    """Serialize data to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, cls=DateTimeEncoder)
        return True
    except Exception as e:
        print(f"Error serializing data to JSON: {e}")
        return False

def ensure_directory_exists(directory_path):
    """Ensure that a directory exists, creating it if necessary."""
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
            return True
        except Exception as e:
            print(f"Error creating directory {directory_path}: {e}")
            return False
    return True