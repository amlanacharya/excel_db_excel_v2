import sys
import os

print("Python Executable:", sys.executable)
print("\nPython Path:")
for path in sys.path:
    print(path)

print("\nCurrent Working Directory:", os.getcwd())

try:
    import excel_db_excel_v2
    print("\nSuccessfully imported excel_db_excel_v2")
    print("Module Location:", excel_db_excel_v2.__file__)
except ImportError as e:
    print("\nFailed to import excel_db_excel_v2:")
    print(e)