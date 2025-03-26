from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
from dotenv import load_dotenv
from excel_nl_query import query_excel_data, load_or_create_vector_store

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

# Create templates directory and HTML file
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
        h1 {
            color: #333;
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
        button {
            padding: 10px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
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
    </style>
</head>
<body>
    <h1>Excel Natural Language Query</h1>
    
    <div class="query-box">
        <input type="text" id="query-input" placeholder="Ask a question about your Excel data...">
        <button id="submit-btn">Submit</button>
    </div>
    
    <div class="sql-query" id="sql-display"></div>
    
    <div class="loading" id="loading">
        <p>Processing your query...</p>
    </div>
    
    <div class="error" id="error" style="display: none;"></div>
    
    <div class="results" id="results"></div>
    
    # Find this section in create_templates() function in excel_query_app.py
# Replace the current examples div with this updated version:

    <div class="examples">
        <h3>Example Questions:</h3>
        <p onclick="setQuery('Show me the total loan amounts by month')">Show me the total loan amounts by month</p>
        <p onclick="setQuery('What was the average deposit amount last quarter?')">What was the average deposit amount last quarter?</p>
        <p onclick="setQuery('List the top 5 largest deposits')">List the top 5 largest deposits</p>
        <p onclick="setQuery('Show depositor names with total deposits over $5000')">Show depositor names with total deposits over $5000</p>
        <p onclick="setQuery('What is the total outstanding loan balance?')">What is the total outstanding loan balance?</p>
        <p onclick="setQuery('Compare deposit totals between January and February')">Compare deposit totals between January and February</p>
    </div>
    
    <div class="system-status" id="system-status">
    </div>

    <script>
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