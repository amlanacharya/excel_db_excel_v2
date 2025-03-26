import os
import sqlite3
import pandas as pd
import json
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter

# Load environment variables
load_dotenv()

# Constants from .env
DB_FILENAME = os.getenv("DATABASE_PATH", "excel_data.db")
CHROMADB_DIR = os.getenv("VECTOR_STORE_PATH", "vectorstore")
EXCEL_FILES = ["Deposits Data Lite.xlsx", "Form X Report  Main Lite.xlsx", "Loans Data Lite.xlsx"]

# Initialize Groq client if API key is available
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None
if GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY
    groq_client = Groq(api_key=GROQ_API_KEY)

# Initialize sentence transformer embeddings (open source)
model_name = "all-MiniLM-L6-v2"  # Smaller, efficient model
embeddings = HuggingFaceEmbeddings(model_name=model_name)

def get_db_schema(db_path=DB_FILENAME):
    """Extract schema from all tabular data tables in the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables created from Excel sheets
    cursor.execute("""
        SELECT workbook, sheet, table_name 
        FROM tabular_data
    """)
    table_mappings = cursor.fetchall()
    
    schema = []
    for workbook, sheet, table_name in table_mappings:
        # Get column information for each table
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        col_info = [f"{col[1]} ({col[2]})" for col in columns]
        
        # Add to schema
        schema.append(f"Table: {table_name} (from {workbook}, sheet {sheet})")
        schema.append(f"Columns: {', '.join(col_info)}")
        
        # Add sample data
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_data = cursor.fetchall()
            if sample_data:
                column_names = [col[1] for col in columns]
                sample_rows = []
                for row in sample_data:
                    sample_row = {column_names[i]: row[i] for i in range(len(column_names))}
                    sample_rows.append(sample_row)
                schema.append(f"Sample data: {json.dumps(sample_rows, default=str)}")
        except Exception as e:
            schema.append(f"Error getting sample data: {str(e)}")
        
        schema.append("\n")
    
    conn.close()
    return "\n".join(schema)

def create_example_queries_from_tables(db_path=DB_FILENAME):
    """Generate example SQL queries based on the available tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT table_name FROM tabular_data")
    tables = cursor.fetchall()
    
    example_queries = []
    
    for table in tables:
        table_name = table[0]
        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        if not columns:
            continue
            
        column_names = [col[1] for col in columns]
        
        # Find date columns
        date_columns = [col for col in column_names if 'date' in col.lower()]
        
        # Find amount or numeric columns
        amount_columns = [col for col in column_names if any(term in col.lower() for term in 
                                                           ['amount', 'sum', 'total', 'value', 'balance'])]
        
        # Find name columns
        name_columns = [col for col in column_names if any(term in col.lower() for term in 
                                                          ['name', 'customer', 'client', 'depositor', 'borrower'])]
        
        # Generate examples based on table structure
        if date_columns and amount_columns:
            # Time-based aggregation example
            date_col = date_columns[0]
            amount_col = amount_columns[0]
            
            example_queries.append(
                f"Query: Show total {amount_col} by month in {table_name}; " +
                f"SQL: SELECT strftime('%Y-%m', {date_col}) as month, SUM({amount_col}) as total FROM {table_name} GROUP BY month ORDER BY month;"
            )
        
        if amount_columns:
            # Simple stats example
            amount_col = amount_columns[0]
            example_queries.append(
                f"Query: What's the average {amount_col} in {table_name}; " +
                f"SQL: SELECT AVG({amount_col}) as average_{amount_col} FROM {table_name};"
            )
            
            example_queries.append(
                f"Query: Find the highest {amount_col} in {table_name}; " +
                f"SQL: SELECT MAX({amount_col}) as max_{amount_col} FROM {table_name};"
            )
        
        if name_columns and amount_columns:
            # Entity aggregation example
            name_col = name_columns[0]
            amount_col = amount_columns[0]
            
            example_queries.append(
                f"Query: List total {amount_col} for each {name_col} in {table_name}; " +
                f"SQL: SELECT {name_col}, SUM({amount_col}) as total FROM {table_name} GROUP BY {name_col} ORDER BY total DESC;"
            )
    
    conn.close()
    return example_queries

def create_vector_store(db_path=DB_FILENAME):
    """Create vector store from database schema and example queries"""
    # Get schema information
    schema = get_db_schema(db_path)
    
    # Generate example queries
    example_queries = create_example_queries_from_tables(db_path)
    
    # Combine all documents
    documents = [schema] + example_queries
    
    # Add financial-specific examples
    financial_examples = [
        "Query: Show all deposits greater than 2000; SQL: SELECT * FROM Deposits_Data_Lite_Sheet1 WHERE Amount > 2000;",
        "Query: Calculate total loan amount by month; SQL: SELECT strftime('%Y-%m', Date) as month, SUM(Amount) as total FROM Loans_Data_Lite_Sheet1 GROUP BY month ORDER BY month;",
        "Query: Find average deposit amount by category; SQL: SELECT Category, AVG(Amount) as avg_amount FROM Deposits_Data_Lite_Sheet1 GROUP BY Category;",
        "Query: List all borrowers with loans above 5% interest; SQL: SELECT Borrower_Name, Amount, Interest_Rate FROM Loans_Data_Lite_Sheet1 WHERE Interest_Rate > 5.0;",
        "Query: Count deposits by category; SQL: SELECT Category, COUNT(*) as count FROM Deposits_Data_Lite_Sheet1 GROUP BY Category;",
        "Query: Show monthly deposit totals for the second quarter; SQL: SELECT strftime('%Y-%m', Date) as month, SUM(Amount) as total FROM Deposits_Data_Lite_Sheet1 WHERE Date BETWEEN '2023-04-01' AND '2023-06-30' GROUP BY month;"
    ]
    
    documents.extend(financial_examples)
    
    # Create vector store
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = []
    for doc in documents:
        texts.extend(text_splitter.split_text(doc))
    
    # Save to disk for reuse
    vector_store = Chroma.from_texts(texts, embeddings, persist_directory=CHROMADB_DIR)
    vector_store.persist()
    
    return vector_store

def load_or_create_vector_store(db_path=DB_FILENAME):
    """Load existing vector store or create a new one"""
    if os.path.exists(CHROMADB_DIR) and os.listdir(CHROMADB_DIR):
        print("Loading existing vector store...")
        return Chroma(persist_directory=CHROMADB_DIR, embedding_function=embeddings)
    else:
        print("Creating new vector store...")
        return create_vector_store(db_path)


def rule_based_sql_generation(query, db_schema):
    """Simple rule-based SQL generation as fallback when no LLM is available"""
    # Extract table names from schema
    import re
    table_match = re.findall(r"Table: (\w+)", db_schema)
    tables = table_match if table_match else ["table_unknown"]
    
    # Extract column names
    column_match = re.findall(r"Columns: (.*)", db_schema)
    column_text = column_match[0] if column_match else ""
    columns = [col.split(" ")[0] for col in column_text.split(", ")]
    
    # Determine operation from query
    query_lower = query.lower()
    
    if any(x in query_lower for x in ["average", "avg", "mean"]):
        for col in columns:
            if col.lower() in query_lower or "amount" in col.lower():
                return f"SELECT AVG({col}) FROM {tables[0]};"
    
    if any(x in query_lower for x in ["sum", "total"]):
        for col in columns:
            if col.lower() in query_lower or "amount" in col.lower():
                return f"SELECT SUM({col}) FROM {tables[0]};"
    
    if any(x in query_lower for x in ["maximum", "max", "highest"]):
        for col in columns:
            if col.lower() in query_lower or "amount" in col.lower():
                return f"SELECT MAX({col}) FROM {tables[0]};"
                
    if "count" in query_lower:
        return f"SELECT COUNT(*) FROM {tables[0]};"
    
    # Default to SELECT *
    return f"SELECT * FROM {tables[0]} LIMIT 10;"

def query_excel_data(nl_query, db_path=DB_FILENAME, vector_store=None, use_ollama=False):
    """Execute natural language query against SQLite database with RAG"""
    # Connect to database
    conn = sqlite3.connect(db_path)
    
    # Get schema for context
    db_schema = get_db_schema(db_path)
    
    # Create or load vector store
    if vector_store is None:
        vector_store = load_or_create_vector_store(db_path)
    
    # Convert to SQL and execute
    try:
        # Pass the database path to nl_to_sql_with_rag
        sql_query = nl_to_sql_with_rag(nl_query, vector_store, db_schema, use_ollama, db_path)
        print(f"Generated SQL: {sql_query}")
        result = pd.read_sql_query(sql_query, conn)
        return result, sql_query
    except Exception as e:
        return f"Error: {str(e)}", ""
    finally:
        conn.close()

def create_ui():
    """Create a simple command-line interface for testing"""
    print("=" * 50)
    print("Excel Natural Language Query System")
    print("=" * 50)
    print("Type 'exit' to quit\n")
    
    # Ensure database exists
    if not os.path.exists(DB_FILENAME):
        print(f"Database {DB_FILENAME} not found. Please run the main.py script first.")
        return
    
    # Create vector store if needed
    vector_store = load_or_create_vector_store()
    
    # Check if we're using Groq or Ollama
    use_ollama = not groq_client
    if use_ollama:
        print("GROQ API key not found in .env. Will use local rule-based generation.")
        print("For better results, add GROQ_API_KEY to your .env file or set up Ollama.")
    
    while True:
        query = input("\nEnter your question about the Excel data: ")
        if query.lower() == 'exit':
            break
        
        print("Processing query...")
        result, sql = query_excel_data(query, vector_store=vector_store, use_ollama=use_ollama)
        
        if isinstance(result, pd.DataFrame):
            if result.empty:
                print("No results found.")
            else:
                print(f"\nGenerated SQL: {sql}")
                print("\nResults:")
                print(result.to_string(index=False))
                print(f"\nRows: {len(result)}")
        else:
            print(result)

def get_all_columns_with_spaces(db_path):
    """Extract all column names with spaces from the database schema"""
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT table_name FROM tabular_data")
    tables = cursor.fetchall()
    
    columns_with_spaces = []
    
    for table in tables:
        table_name = table[0]
        
        # Get column information for the table
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        # Check each column name for spaces
        for col in columns:
            col_name = col[1]  # Column name is in position 1
            if ' ' in col_name:
                columns_with_spaces.append(col_name)
    
    conn.close()
    return columns_with_spaces

def escape_column_names(sql_query, db_path="excel_data.db"):
    """
    Process an SQL query to properly escape column names that contain spaces
    by enclosing them in double quotes.
    """
    import re
    
    # Get actual column names with spaces from the database
    try:
        columns_with_spaces = get_all_columns_with_spaces(db_path)
    except Exception as e:
        print(f"Error getting column names from database: {e}")
        # Fallback to common column names
        columns_with_spaces = [
            "Business Date",
            "Outstanding Principal Amount",
            "Current Balance",
            "Loan Amount",
            "Interest Rate",
            "Customer Name",
            "Due Date",
            "Transaction Date",
            "Account Number",
            "Payment Date",
            "Deposit Date",
            "Depositor Name",
            "Transaction Type"
        ]
    
    # Sort by length (descending) to avoid partial replacements
    columns_with_spaces.sort(key=len, reverse=True)
    
    # Replace unquoted column names with quoted ones
    processed_sql = sql_query
    
    for col in columns_with_spaces:
        # Careful pattern to find column names not already quoted
        # Look for column name not preceded by " or [ and not followed by " or ]
        pattern = r'(?<!["\[])' + re.escape(col) + r'(?!["\]])'
        replacement = f'"{col}"'
        processed_sql = re.sub(pattern, replacement, processed_sql)
    
    # Also replace patterns where function arguments aren't quoted
    # E.g., SUM(Current Balance) -> SUM("Current Balance")
    function_pattern = r'(AVG|SUM|COUNT|MIN|MAX|GROUP BY|ORDER BY)\s*\(\s*([^"(][^()]*[^")])\s*\)'
    
    def replace_func_args(match):
        func = match.group(1)
        args = match.group(2)
        
        # Check if args contain any columns with spaces
        for col in columns_with_spaces:
            if col in args and f'"{col}"' not in args:
                args = args.replace(col, f'"{col}"')
        
        return f"{func}({args})"
    
    processed_sql = re.sub(function_pattern, replace_func_args, processed_sql)
    
    print(f"Original SQL: {sql_query}")
    print(f"Processed SQL: {processed_sql}")
    
    return processed_sql

def nl_to_sql_with_rag(query, vector_store, db_schema, use_ollama=False, db_path="excel_data.db"):
    """Convert natural language to SQL using RAG and Llama via Groq or Ollama"""
    # Retrieve relevant context
    relevant_docs = vector_store.similarity_search(query, k=5)
    context = "\n".join([doc.page_content for doc in relevant_docs])
    
    system_prompt = f"""
    You are an expert SQL analyst for Excel financial data. Convert the natural language query to a valid SQLite SQL query.
    
    Database schema:
    {db_schema}
    
    Relevant examples and context:
    {context}
    
    IMPORTANT: When writing SQL, always enclose column names that contain spaces in double quotes or square brackets.
    For example: 
    - SELECT "Business Date", "Outstanding Principal Amount" FROM table
    - SELECT [Business Date], [Outstanding Principal Amount] FROM table
    
    Pay careful attention to column names inside functions like SUM(), AVG(), etc. These also need to be quoted if they contain spaces.
    
    Return ONLY the SQL query without explanation, comments or markdown formatting.
    """
    
    # Use Ollama if specified, otherwise use Groq if available
    if use_ollama:
        try:
            from langchain_community.llms import Ollama
            ollama = Ollama(model="llama3")
            response = ollama.invoke(
                f"System: {system_prompt}\n\nUser: Generate SQL for: {query}"
            )
            sql_query = response.strip()
        except Exception as e:
            print(f"Error using Ollama: {e}")
            print("Falling back to rule-based SQL generation...")
            sql_query = rule_based_sql_generation(query, db_schema)
    elif groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate SQL for: {query}"}
                ],
                temperature=0.1,
                max_tokens=500
            )
            sql_query = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error using Groq: {e}")
            print("Falling back to rule-based SQL generation...")
            sql_query = rule_based_sql_generation(query, db_schema)
    else:
        print("No LLM service available. Using rule-based SQL generation.")
        sql_query = rule_based_sql_generation(query, db_schema)
    
    # Process SQL to handle column names with spaces properly
    # Pass the database path to the escape_column_names function
    sql_query = escape_column_names(sql_query, db_path)
    sql_query = clean_sql_query(sql_query)
    return sql_query

def clean_sql_query(sql_query):
    """Remove markdown code formatting and other unwanted characters from SQL query."""
    import re
    
    # Remove Markdown code block markers with language
    sql_query = re.sub(r'```sql\s*|\s*```', '', sql_query)
    
    # Remove Markdown code block markers without language
    sql_query = re.sub(r'```\s*|\s*```', '', sql_query)
    
    # Remove single backticks
    sql_query = re.sub(r'^`|`$', '', sql_query)
    
    return sql_query.strip()


if __name__ == "__main__":
    create_ui()