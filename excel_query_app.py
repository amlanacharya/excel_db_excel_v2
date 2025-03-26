from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
from dotenv import load_dotenv
from excel_nl_query import query_excel_data, load_or_create_vector_store
import sqlite3
# Load environment variables
load_dotenv()

# Get configuration from .env
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

app = Flask(__name__)

# Global variable to store vector store
vector_store = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    global vector_store
    
    # Get query from request
    nl_query = request.json.get('query', '')
    
    # Initialize vector store if not already done
    if vector_store is None:
        vector_store = load_or_create_vector_store()
    
    # Check if Groq API key is available
    groq_api_key = os.getenv("GROQ_API_KEY")
    use_ollama = not groq_api_key
    
    # Process query
    result, sql_query = query_excel_data(nl_query, vector_store=vector_store, use_ollama=use_ollama)
    
    # Convert result to JSON
    if isinstance(result, pd.DataFrame):
        return jsonify({
            'success': True,
            'data': result.to_dict(orient='records'),
            'columns': result.columns.tolist(),
            'rowCount': len(result),
            'sql': sql_query
        })
    else:
        return jsonify({
            'success': False,
            'error': str(result)
        })



@app.route('/api/schema')
def get_schema():
    """Return database schema information for all tables"""
    try:
        import sqlite3
        from sqlite3 import Error
        
        db_path = os.getenv("DATABASE_PATH", "excel_data.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema = {}
        
        # Exclude sqlite system tables
        for table in tables:
            table_name = table[0]
            if table_name.startswith('sqlite_'):
                continue
                
            # Get column information for each table
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            # Format column info
            column_info = []
            for col in columns:
                column_info.append({
                    'name': col[1],
                    'type': col[2],
                    'pk': col[5] == 1
                })
            
            # Add sample data (first 3 rows)
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                sample_rows = cursor.fetchall()
                sample_data = []
                
                for row in sample_rows:
                    sample_row = {}
                    for i, col in enumerate(columns):
                        sample_row[col[1]] = row[i]
                    sample_data.append(sample_row)
            except Exception as e:
                sample_data = [{"error": str(e)}]
            
            schema[table_name] = {
                'columns': column_info,
                'sample_data': sample_data
            }
        
        conn.close()
        return jsonify({'success': True, 'schema': schema})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/execute_sql', methods=['POST'])
def execute_sql():
    """Execute raw SQL query"""
    try:
        sql_query = request.json.get('query', '')
        
        if not sql_query:
            return jsonify({'success': False, 'error': 'No query provided'})
        
        # Clean any markdown formatting that might be in the query
        sql_query = clean_sql_query(sql_query)
        
        # Connect to database
        db_path = os.getenv("DATABASE_PATH", "excel_data.db")
        conn = sqlite3.connect(db_path)
        
        # Execute query and convert to dataframe
        result = pd.read_sql_query(sql_query, conn)
        
        # Convert to JSON response
        return jsonify({
            'success': True,
            'data': result.to_dict(orient='records'),
            'columns': result.columns.tolist(),
            'rowCount': len(result),
            'sql': sql_query
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Add this cleaning function used in execute_sql
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

# Modify the create_templates function to include the new UI elements
def create_templates():
    os.makedirs('templates', exist_ok=True)
    
    with open('templates/index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Excel Natural Language Query</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        h1, h2, h3 {
            color: #333;
        }
        h1 {
            margin-bottom: 20px;
        }
        .query-box {
            margin-bottom: 20px;
        }
        input[type="text"] {
            width: 70%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        textarea {
            width: 100%;
            height: 150px;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: monospace;
        }
        button {
            padding: 10px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-right: 10px;
        }
        button:hover {
            background-color: #45a049;
        }
        .results {
            margin-top: 20px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .loading {
            display: none;
            margin-top: 20px;
        }
        .error {
            color: red;
            margin-top: 20px;
        }
        .examples {
            margin-top: 30px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }
        .examples h3 {
            margin-top: 0;
        }
        .examples p {
            cursor: pointer;
            color: #0066cc;
        }
        .examples p:hover {
            text-decoration: underline;
        }
        .sql-query {
            font-family: monospace;
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            white-space: pre-wrap;
            display: none;
        }
        .system-status {
            margin-top: 30px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
            font-size: 14px;
            color: #666;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background-color: #f0f0f0;
            border: 1px solid #ddd;
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            margin-right: 5px;
        }
        .tab.active {
            background-color: white;
            border-bottom: 1px solid white;
        }
        .tab-content {
            display: none;
            padding: 20px;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 4px 4px;
        }
        .tab-content.active {
            display: block;
        }
        .schema-container {
            margin-top: 20px;
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
        }
        .table-item {
            margin-bottom: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
        }
        .table-header {
            background-color: #e9ecef;
            padding: 10px;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
        }
        .table-content {
            display: none;
            padding: 15px;
            background-color: white;
        }
        .column-list {
            list-style-type: none;
            padding: 0;
            margin: 0;
        }
        .column-item {
            padding: 5px;
            border-bottom: 1px solid #eee;
            font-family: monospace;
        }
        .column-item:last-child {
            border-bottom: none;
        }
        .primary-key {
            color: #d63384;
            font-weight: bold;
        }
        .copy-btn {
            background-color: #6c757d;
            color: white;
            padding: 2px 8px;
            font-size: 12px;
            border-radius: 3px;
            cursor: pointer;
        }
        .copy-btn:hover {
            background-color: #5a6268;
        }
        .sql-builder {
            margin-top: 20px;
        }
        .sample-data {
            font-size: 14px;
            margin-top: 10px;
        }
        .sample-data table {
            font-size: 12px;
        }
    </style>
</head>
<body>
    <h1>Excel Natural Language Query</h1>
    
    <div class="tabs">
        <div class="tab active" onclick="openTab('natural-language')">Natural Language</div>
        <div class="tab" onclick="openTab('sql-query')">Custom SQL</div>
        <div class="tab" onclick="openTab('schema-explorer')">Schema Explorer</div>
    </div>
    
    <div id="natural-language" class="tab-content active">
        <div class="query-box">
            <input type="text" id="query-input" placeholder="Ask a question about your Excel data...">
            <button id="submit-btn">Submit</button>
        </div>
        
        <div class="examples">
            <h3>Example Questions:</h3>
            <p onclick="setQuery('Show me the total loan amounts by month')">Show me the total loan amounts by month</p>
            <p onclick="setQuery('What was the average deposit amount last quarter?')">What was the average deposit amount last quarter?</p>
            <p onclick="setQuery('List the top 5 largest deposits')">List the top 5 largest deposits</p>
            <p onclick="setQuery('Show depositor names with total deposits over $5000')">Show depositor names with total deposits over $5000</p>
            <p onclick="setQuery('What is the total outstanding loan balance?')">What is the total outstanding loan balance?</p>
            <p onclick="setQuery('Compare deposit totals between January and February')">Compare deposit totals between January and February</p>
        </div>
    </div>
    
    <div id="sql-query" class="tab-content">
        <h2>Custom SQL Query</h2>
        <p>Write your own SQL query to access the database directly:</p>
        <textarea id="sql-textarea" placeholder="SELECT * FROM Deposits_Data_Lite_Sheet1 LIMIT 10;"></textarea>
        <div style="margin-top: 10px;">
            <button id="execute-sql-btn">Execute SQL</button>
        </div>
    </div>
    
    <div id="schema-explorer" class="tab-content">
        <h2>Database Schema Explorer</h2>
        <p>Explore tables and columns to help build your queries:</p>
        <div id="schema-container" class="schema-container">
            <div class="loading" id="schema-loading">Loading schema information...</div>
        </div>
    </div>
    
    <div class="sql-query" id="sql-display"></div>
    
    <div class="loading" id="loading">
        <p>Processing your query...</p>
    </div>
    
    <div class="error" id="error" style="display: none;"></div>
    
    <div class="results" id="results"></div>
    
    <div class="system-status" id="system-status"></div>

    <script>
        // Tab functionality
        function openTab(tabName) {
            // Hide all tab contents
            var tabContents = document.getElementsByClassName("tab-content");
            for (var i = 0; i < tabContents.length; i++) {
                tabContents[i].classList.remove("active");
            }
            
            // Remove active class from all tabs
            var tabs = document.getElementsByClassName("tab");
            for (var i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove("active");
            }
            
            // Activate the selected tab
            document.getElementById(tabName).classList.add("active");
            
            // Find the tab button and activate it
            for (var i = 0; i < tabs.length; i++) {
                if (tabs[i].textContent.toLowerCase().includes(tabName.replace('-', ' '))) {
                    tabs[i].classList.add("active");
                }
            }
            
            // Load schema if schema explorer tab is selected
            if (tabName === 'schema-explorer' && !document.getElementById('schema-container').innerHTML.includes('table-item')) {
                loadSchema();
            }
        }
        
        // Check if we're using Groq or local processing
        fetch('/api/system-status')
            .then(response => response.json())
            .then(data => {
                const statusElement = document.getElementById('system-status');
                if (data.usingGroq) {
                    statusElement.innerHTML = "System is using Groq API for improved accuracy.";
                } else {
                    statusElement.innerHTML = "System is using local processing. For better results, add a Groq API key.";
                }
            })
            .catch(error => {
                console.error('Error checking system status:', error);
            });

        document.getElementById('submit-btn').addEventListener('click', submitQuery);
        document.getElementById('query-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                submitQuery();
            }
        });
        
        document.getElementById('execute-sql-btn').addEventListener('click', executeSQL);

        function loadSchema() {
            const schemaContainer = document.getElementById('schema-container');
            const loadingElement = document.getElementById('schema-loading');
            loadingElement.style.display = 'block';
            
            fetch('/api/schema')
                .then(response => response.json())
                .then(data => {
                    loadingElement.style.display = 'none';
                    
                    if (data.success) {
                        const schema = data.schema;
                        let schemaHTML = '';
                        
                        for (const tableName in schema) {
                            const tableInfo = schema[tableName];
                            const columns = tableInfo.columns;
                            const sampleData = tableInfo.sample_data;
                            
                            schemaHTML += `
                                <div class="table-item">
                                    <div class="table-header" onclick="toggleTableContent('${tableName}')">
                                        <span>${tableName}</span>
                                        <span class="copy-btn" onclick="event.stopPropagation(); copyTableName('${tableName}')">Copy</span>
                                    </div>
                                    <div class="table-content" id="table-${tableName}">
                                        <h4>Columns:</h4>
                                        <ul class="column-list">`;
                            
                            columns.forEach(col => {
                                const isPK = col.pk ? 'primary-key' : '';
                                schemaHTML += `
                                    <li class="column-item ${isPK}">
                                        ${col.name} (${col.type})
                                        <span class="copy-btn" onclick="copyColumnName('${col.name}')">Copy</span>
                                    </li>`;
                            });
                            
                            schemaHTML += `</ul>
                                        <div class="sample-data">
                                            <h4>Sample Data:</h4>`;
                            
                            if (sampleData && sampleData.length > 0) {
                                schemaHTML += '<table><thead><tr>';
                                
                                // Create headers
                                const firstRow = sampleData[0];
                                for (const key in firstRow) {
                                    schemaHTML += `<th>${key}</th>`;
                                }
                                schemaHTML += '</tr></thead><tbody>';
                                
                                // Add data rows
                                sampleData.forEach(row => {
                                    schemaHTML += '<tr>';
                                    for (const key in firstRow) {
                                        schemaHTML += `<td>${row[key] !== null ? row[key] : ''}</td>`;
                                    }
                                    schemaHTML += '</tr>';
                                });
                                
                                schemaHTML += '</tbody></table>';
                            } else {
                                schemaHTML += '<p>No sample data available</p>';
                            }
                            
                            schemaHTML += `</div>
                                        <div class="sql-builder">
                                            <button onclick="generateSelectSQL('${tableName}')">Generate SELECT</button>
                                        </div>
                                    </div>
                                </div>`;
                        }
                        
                        schemaContainer.innerHTML = schemaHTML;
                    } else {
                        schemaContainer.innerHTML = `<div class="error">Error loading schema: ${data.error}</div>`;
                    }
                })
                .catch(error => {
                    loadingElement.style.display = 'none';
                    schemaContainer.innerHTML = `<div class="error">Error loading schema: ${error.message}</div>`;
                });
        }
        
        function toggleTableContent(tableName) {
            const tableContent = document.getElementById(`table-${tableName}`);
            if (tableContent.style.display === 'block') {
                tableContent.style.display = 'none';
            } else {
                tableContent.style.display = 'block';
            }
        }
        
        function copyTableName(tableName) {
            navigator.clipboard.writeText(tableName);
            alert(`Copied "${tableName}" to clipboard`);
        }
        
        function copyColumnName(columnName) {
            navigator.clipboard.writeText(columnName);
            alert(`Copied "${columnName}" to clipboard`);
        }
        
        function generateSelectSQL(tableName) {
            const sql = `SELECT * FROM ${tableName} LIMIT 10;`;
            document.getElementById('sql-textarea').value = sql;
            openTab('sql-query');
        }

        function setQuery(query) {
            document.getElementById('query-input').value = query;
            submitQuery();
        }

        function submitQuery() {
            const query = document.getElementById('query-input').value.trim();
            if (!query) return;
            
            // Show loading, hide results and error
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').innerHTML = '';
            document.getElementById('error').style.display = 'none';
            document.getElementById('sql-display').style.display = 'none';
            
            fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query }),
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                
                if (data.success) {
                    renderTable(data.data, data.columns);
                    
                    // Display SQL query if available
                    const sqlElement = document.getElementById('sql-display');
                    if (data.sql) {
                        sqlElement.textContent = data.sql;
                        sqlElement.style.display = 'block';
                    }
                } else {
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(error => {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').textContent = 'An error occurred: ' + error.message;
                document.getElementById('error').style.display = 'block';
            });
        }
        
        function executeSQL() {
            const sqlQuery = document.getElementById('sql-textarea').value.trim();
            if (!sqlQuery) return;
            
            // Show loading, hide results and error
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').innerHTML = '';
            document.getElementById('error').style.display = 'none';
            document.getElementById('sql-display').style.display = 'none';
            
            fetch('/execute_sql', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: sqlQuery }),
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                
                if (data.success) {
                    renderTable(data.data, data.columns);
                    
                    // Display SQL query
                    const sqlElement = document.getElementById('sql-display');
                    sqlElement.textContent = data.sql;
                    sqlElement.style.display = 'block';
                } else {
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(error => {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').textContent = 'An error occurred: ' + error.message;
                document.getElementById('error').style.display = 'block';
            });
        }

        function renderTable(data, columns) {
            if (!data || data.length === 0) {
                document.getElementById('results').innerHTML = '<p>No results found.</p>';
                return;
            }
            
            let tableHTML = '<table><thead><tr>';
            
            // Add headers
            columns.forEach(column => {
                tableHTML += `<th>${column}</th>`;
            });
            tableHTML += '</tr></thead><tbody>';
            
            // Add rows
            data.forEach(row => {
                tableHTML += '<tr>';
                columns.forEach(column => {
                    tableHTML += `<td>${row[column] !== null ? row[column] : ''}</td>`;
                });
                tableHTML += '</tr>';
            });
            
            tableHTML += '</tbody></table>';
            document.getElementById('results').innerHTML = tableHTML;
        }
    </script>
</body>
</html>
        ''')
# Add endpoint to check if we're using Groq
@app.route('/api/system-status')
def system_status():
    groq_api_key = os.getenv("GROQ_API_KEY")
    return jsonify({
        'usingGroq': bool(groq_api_key)
    })

if __name__ == '__main__':
    create_templates()
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)