# Local MCP stdio verification

Date: 2026-10-23

## Result

The three ARA servers were launched as separate stdio subprocesses through the official MCP SDK client wrapper. The client listed the expected tools from each server and called `score_chunks`, which returned the typed `not_ready` result. The integration test is `tests/test_mcp_stdio_servers.py`.

| Server | Tools listed | Result |
|---|---|---|
| `ara-rag-mcp` | `search_knowledge_base`, `get_chunk` | Started over stdio |
| `ara-web-search-mcp` | `web_search`, `fetch_page` | Started over stdio; the live search backend was not called |
| `ara-dl-model-mcp` | `score_chunks` | Started over stdio; returned `not_ready` as expected |

Run the protocol-level check from the repository root with:

```powershell
uv run --locked pytest tests/test_mcp_stdio_servers.py
```

This validates MCP stdio startup and tool discovery from a local client. Claude Desktop itself was not launched or configured in this environment, so its UI-level connection remains unverified. The sample config is `docs/claude_desktop_config.example.json`; replace both path placeholders with absolute paths, then use Claude Desktop's **Settings > Developer > Edit Config** to open the active configuration file. A local server must use a stdio entry and an executable path the desktop process can resolve. The official [MCP client transport guide](https://py.sdk.modelcontextprotocol.io/client/transports/) describes stdio subprocess lifecycle; Anthropic's [local MCP guide](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop) describes current Desktop extension and local server setup.
