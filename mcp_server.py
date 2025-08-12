import sqlite3
from mcp.server.fastmcp import FastMCP
import os

mcp = FastMCP("Demo MCP Server")

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

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def add_magic_number(a: int) -> int:
    """Add a magic number to the given number"""
    return a + 42

@mcp.tool()
def show_files_in_folder(path: str) -> list[str]:
    """Show files in a folder"""
    return os.listdir(path)

@mcp.tool()
def get_str_permutation(s: str) -> list[str]:
    """Get all permutations of a string"""
    if len(s) == 1:
        return [s]
    permutations = []
    for i in range(len(s)):
        char = s[i]
        remaining_chars = s[:i] + s[i+1:]
        for permutation in get_str_permutation(remaining_chars):
            permutations.append(char + permutation)
    return permutations

if __name__ == "__main__":
    mcp.run(transport="stdio")
