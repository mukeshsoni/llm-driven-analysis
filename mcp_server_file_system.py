import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Magic add mcp server")

@mcp.tool()
def show_files_in_folder(path: str) -> list[str]:
    """Show files in a folder"""
    return os.listdir(path)

if __name__ == "__main__":
    mcp.run(transport="stdio")
