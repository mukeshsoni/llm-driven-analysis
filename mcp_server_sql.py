import sqlite3
from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Any, Optional
import os
import glob

mcp = FastMCP("SQL execution mcp server")

# Configuration for multiple databases
# In production, this could come from environment variables or config files
DATABASE_CONFIG = {
    "chinook": {
        "path": "chinook.db",
        "description": "Music store database with artists, albums, and sales data"
    },
    "employees": {
        "path": "employees.db",
        "description": "Employee management database with departments, employees, and projects"
    }
}

# Auto-discover .db files in current directory if not in config
def discover_databases() -> Dict[str, Dict[str, str]]:
    """
    Discover all SQLite databases in the current directory.
    Returns a dict with database names and their configurations.
    """
    databases = DATABASE_CONFIG.copy()

    # Find all .db files in current directory
    for db_file in glob.glob("*.db"):
        # Extract name without extension
        db_name = os.path.splitext(db_file)[0]

        # Skip if already in config
        if db_name not in databases:
            databases[db_name] = {
                "path": db_file,
                "description": f"Auto-discovered SQLite database: {db_file}"
            }

    return databases

def get_database_schema(db_path: str) -> Dict[str, Any]:
    """
    Extract the complete schema from the SQLite database.

    Returns:
        dict: Database schema with tables, columns, and foreign keys
    """
    schema = {
        "database": db_path,
        "tables": {}
    }

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = cursor.fetchall()

            for (table_name,) in tables:
                # Get table info (columns)
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns_info = cursor.fetchall()

                columns = []
                for col in columns_info:
                    col_id, name, col_type, not_null, default, is_pk = col
                    columns.append({
                        "name": name,
                        "type": col_type,
                        "nullable": not not_null,
                        "primary_key": bool(is_pk),
                        "default": default
                    })

                # Get foreign keys
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fk_info = cursor.fetchall()

                foreign_keys = []
                for fk in fk_info:
                    fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
                    foreign_keys.append({
                        "column": from_col,
                        "references_table": ref_table,
                        "references_column": to_col
                    })

                schema["tables"][table_name] = {
                    "columns": columns,
                    "foreign_keys": foreign_keys
                }
    except Exception as e:
        schema["error"] = str(e)

    return schema

def format_schema_for_prompt(schema: Dict[str, Any]) -> str:
    """
    Format the schema dictionary into a human-readable string for the LLM prompt.

    Returns:
        str: Formatted schema description
    """
    if "error" in schema:
        return f"Error reading schema: {schema['error']}"

    lines = ["Database Schema:"]
    lines.append("=" * 50)

    for table_name, table_info in schema["tables"].items():
        # Build column list
        column_parts = []
        for col in table_info["columns"]:
            col_str = col["name"]
            if col["primary_key"]:
                col_str += " (PK)"
            column_parts.append(col_str)

        # Add foreign key information
        fk_parts = []
        for fk in table_info["foreign_keys"]:
            fk_parts.append(f"{fk['column']} -> {fk['references_table']}.{fk['references_column']}")

        # Format table line
        table_line = f"• {table_name}({', '.join(column_parts)})"
        if fk_parts:
            table_line += f"\n  Foreign Keys: {', '.join(fk_parts)}"

        lines.append(table_line)

    return "\n".join(lines)

# Resource: List of available databases
@mcp.resource(uri="databases://list")
def list_databases_resource() -> str:
    """
    Get the list of available databases.

    Returns:
        str: JSON formatted list of databases with their descriptions
    """
    import json
    databases = discover_databases()

    db_list = []
    for name, config in databases.items():
        db_list.append({
            "name": name,
            "path": config["path"],
            "description": config["description"],
            "schema_uri": f"schema://{name}"
        })

    return json.dumps({
        "databases": db_list,
        "count": len(db_list)
    }, indent=2)

# Dynamic schema resources for each database
def register_schema_resources():
    """
    Dynamically register schema resources for all discovered databases.
    """
    databases = discover_databases()

    for db_name, config in databases.items():
        # Create a closure to capture the database path
        def make_schema_resource(db_path: str, name: str):
            def get_schema_resource() -> str:
                """Get the database schema as a resource."""
                schema = get_database_schema(db_path)
                if "error" in schema:
                    return f"Error accessing {name} database: {schema['error']}"
                return format_schema_for_prompt(schema)
            return get_schema_resource

        # Register the resource with a unique URI for each database
        resource_func = make_schema_resource(config["path"], db_name)
        resource_func.__name__ = f"get_{db_name}_schema"
        resource_func.__doc__ = f"Get the schema for {db_name} database"

        mcp.resource(uri=f"schema://{db_name}")(resource_func)

# Register schema resources at module load time
register_schema_resources()

@mcp.tool()
def list_databases() -> Dict[str, Any]:
    """
    Get the list of available databases that can be queried.

    Returns:
        dict: List of available databases with their names and descriptions
    """
    databases = discover_databases()

    db_list = []
    for name, config in databases.items():
        db_list.append({
            "name": name,
            "description": config["description"]
        })

    return {
        "databases": db_list,
        "count": len(db_list)
    }

@mcp.tool()
def get_schema(database: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the complete database schema including all tables, columns, and relationships.

    Args:
        database: Name of the database (optional, defaults to 'chinook')

    Returns:
        dict: Complete database schema with tables, columns, types, and foreign keys
    """
    databases = discover_databases()

    # Default to chinook if not specified
    if database is None:
        database = "chinook"

    if database not in databases:
        return {
            "error": f"Database '{database}' not found. Available databases: {', '.join(databases.keys())}"
        }

    db_path = databases[database]["path"]
    return get_database_schema(db_path)

@mcp.tool()
def run_query(query: str, database: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a sqlite SELECT query on the specified database. Only SELECT queries are allowed.

    Args:
        query: The sqlite SELECT query to execute
        database: Name of the database to query (optional, defaults to 'chinook')

    Returns:
        dict: Query results with columns and rows, or error message
    """
    databases = discover_databases()

    # Default to chinook if not specified
    if database is None:
        database = "chinook"

    if database not in databases:
        return {
            "error": f"Database '{database}' not found. Available databases: {', '.join(databases.keys())}",
            "rows": [],
            "columns": [],
            "row_count": 0
        }

    db_path = databases[database]["path"]

    # Basic safety check - only allow SELECT queries
    query_lower = query.strip().lower()
    if not query_lower.startswith('select') and not query_lower.startswith('with'):
        return {
            "error": "Only SELECT queries are allowed",
            "rows": [],
            "columns": [],
            "row_count": 0
        }

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            return {
                "database": database,
                "rows": rows,
                "columns": columns,
                "row_count": len(rows)
            }
    except Exception as e:
        return {
            "error": str(e),
            "database": database,
            "rows": [],
            "columns": [],
            "row_count": 0
        }

if __name__ == "__main__":
    mcp.run(transport="stdio")
