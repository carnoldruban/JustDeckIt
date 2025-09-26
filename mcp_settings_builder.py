#!/usr/bin/env python3
import json

# MCP settings data structure
mcp_settings = {
    "mcpServers": {
        "browser": {
            "command": "node",
            "args": ["C:\\Users\\User\\Documents\\Cline\\MCP\\browser-interaction-server\\build\\index.js"],
            "disabled": False
        }
    }
}

# Write to MCP settings file
settings_path = r"c:\Users\User\AppData\Roaming\Windsurf\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"

with open(settings_path, 'w', encoding='utf-8') as f:
    json.dump(mcp_settings, f, indent=None, separators=(',', ':'))

print(f"MCP settings file created successfully at: {settings_path}")
print("JSON Contents:")
print(json.dumps(mcp_settings, indent=2))
