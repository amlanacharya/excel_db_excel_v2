import os
import sys
import argparse
import importlib.util
import shutil

def check_module_exists(module_name):
    """Check if a Python module exists/is installed"""
    try:
        if module_name == "sqlite3":  # Part of standard library
            return True
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False

def install_requirements():
    """Install required packages"""
    requirements = [
        'flask', 
        'pandas', 
        'openpyxl', 
        'sqlite3',  
        'groq', 
        'langchain', 
        'langchain-community', 
        'sentence-transformers',
        'chromadb',
        'python-dotenv'
    ]
    
    missing = [req for req in requirements if not check_module_exists(req)]
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        import subprocess
        for package in missing:
            # Skip sqlite3 as it's part of the standard library
            if package != 'sqlite3':
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def setup_dotenv():
    """Create .env file if it doesn't exist"""
    if not os.path.exists('.env'):
        if os.path.exists('.env.template'):
            shutil.copy('.env.template', '.env')
            print("Created .env file from template.")
            print("Please edit .env file to add your API keys.")
        else:
            # Create .env file
            with open('.env', 'w') as f:
                f.write("""# API configuration
GROQ_API_KEY=

# Database configuration 
DATABASE_PATH=excel_data.db

# Vector store configuration
VECTOR_STORE_PATH=vectorstore

# Server configuration
PORT=5000
DEBUG=True
""")
            print("Created new .env file.")
            print("Please edit .env file to add your API keys.")

def check_credentials():
    """Check if API keys are set in .env file"""
    from dotenv import load_dotenv
    load_dotenv()
    
    groq_key = os.environ.get("GROQ_API_KEY")
    
    if not groq_key:
        print("\nWARNING: GROQ_API_KEY not found in .env file.")
        print("For better SQL generation, please add your Groq API key to the .env file.")
        print("The system will use rule-based SQL generation as a fallback.\n")

def run_excel_processing():
    """Run the Excel processing from main.py"""
    import main
    main.main()

def run_vector_indexing():
    """Create the vector store for RAG"""
    from excel_nl_query import create_vector_store
    create_vector_store()

def run_web_app():
    """Run the Flask web application"""
    from excel_query_app import app
    from dotenv import load_dotenv
    load_dotenv()
    
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print(f"Starting web application on port {port}...")
    app.run(debug=debug, host='0.0.0.0', port=port)

def run_cli():
    """Run the command-line interface"""
    from excel_nl_query import create_ui
    create_ui()

def main():
    parser = argparse.ArgumentParser(description='Excel Natural Language Query System')
    parser.add_argument('--process', action='store_true', help='Process Excel files and create database')
    parser.add_argument('--index', action='store_true', help='Create vector index for RAG')
    parser.add_argument('--web', action='store_true', help='Start web application')
    parser.add_argument('--cli', action='store_true', help='Start command-line interface')
    parser.add_argument('--all', action='store_true', help='Run all steps (process, index, web)')
    parser.add_argument('--setup', action='store_true', help='Setup environment (.env file and dependencies)')
    
    args = parser.parse_args()
    
    # Setup environment if requested or if running all steps
    if args.setup or args.all:
        install_requirements()
        setup_dotenv()
    
    # Check credentials
    check_credentials()
    
    # Execute requested actions
    if args.all or args.process:
        print("Processing Excel files...")
        run_excel_processing()
    
    if args.all or args.index:
        print("Creating vector index...")
        run_vector_indexing()
    
    if args.all or args.web:
        print("Starting web application...")
        run_web_app()
    
    if args.cli:
        print("Starting command-line interface...")
        run_cli()
    
    # If no arguments provided, show help
    if not (args.process or args.index or args.web or args.cli or args.all or args.setup):
        parser.print_help()

if __name__ == "__main__":
    main()