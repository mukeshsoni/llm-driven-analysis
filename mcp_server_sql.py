import sqlite3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SQL execution mcp server")

@mcp.tool()
def run_query(query: str):
    """
    Execute a sqlite SELECT query. Only SELECT queries are allowed.

    Args:
        query: The sqlite SELECT query to execute

    Returns:
        dict: Query results with columns and rows, or error message
    """
    db = 'chinook.db'
    print("running query", query)
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return {
            "rows": rows,
            "columns": columns,
            "row_count": len(rows)
        }

if __name__ == "__main__":
    mcp.run(transport="stdio")
