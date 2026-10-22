# MCP tools and resources have different control flows

An MCP tool is a callable operation that a model can request through the host. A resource is information the application can choose to load into context. A prompt is a reusable message template selected by a user or application. These roles matter because reading evidence and taking an action are different kinds of request.

Tool arguments should be validated at the server boundary, and tool output should be treated as data. The caller should check error indicators and validate returned fields before relying on them. A protocol connection provides a standard way to exchange messages, but the application still owns its trust and authorization rules.

Reference: [MCP Python SDK first steps](https://py.sdk.modelcontextprotocol.io/get-started/first-steps/); [MCP architecture overview](https://modelcontextprotocol.io/docs/concepts/architecture).

