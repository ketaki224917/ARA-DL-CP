# Retrieved text is evidence, not an instruction channel

Documents and web pages can contain text that looks like a command to the model. A research assistant should mark retrieved content as untrusted source material, keep system and developer instructions separate, and tell the model not to follow instructions embedded inside evidence. The application should also restrict which tools may be called and validate tool arguments independently.

This boundary does not make prompt injection impossible. It reduces confusion between the question, the agent's instructions, and the material being analyzed. Test with documents that contain hostile instructions, and confirm that the researcher summarizes their factual content without executing their requests.

Reference: [MCP architecture overview](https://modelcontextprotocol.io/docs/concepts/architecture); ARA security design note, original text licensed under CC BY 4.0.

