from mcp.server.mcpserver import MCPServer

# Inicjalizacja serwera MCP dla systemu Spiżarnik AI (Spiżarnia Bez Dna Sp. z o.o.)
mcp = MCPServer("Spizarnik AI Server")

@mcp.tool()
def hello_spizarnik() -> str:
    """Funkcja testowa weryfikująca połączenie z serwerem MCP."""
    return "Serwer Spiżarnik AI działa poprawnie!"

if __name__ == "__main__":
    mcp.run()