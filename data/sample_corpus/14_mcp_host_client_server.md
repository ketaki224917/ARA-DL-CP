# MCP separates the host, client, and server roles

The Model Context Protocol uses a host-client-server structure. The host is the AI application coordinating work. It creates a client connection for each MCP server. A server offers context or operations to the connected client, and may run locally or remotely depending on its transport.

MCP standardizes context exchange; it does not decide how an application plans a report or what an LLM should do with returned data. Keeping those responsibilities separate lets the host use several independent servers while retaining its own policy for evidence selection, budgets, and report construction.

Reference: [MCP architecture overview](https://modelcontextprotocol.io/docs/concepts/architecture). Documentation license: CC BY 4.0 for documentation contributions; specification content has separate licensing terms.

