# MCP Server Session Management
- If a special `session_start` function exists, invoke it when a user first starts interacting with the server.
- Alternatively, inject some notion of session and user name in the tool calling, similar to the file setup.

# [X] File Return Handling
- If a file returned type is an image, or has field `custom_html`, then render in addition to allowing download. [X]

# MCP Marketplace & Selection
- Create a different route `/marketplace`.
  - Show different possible MCPs, allow selecting, then on the main UI, only show the user-selected MCP.
  - Would need to set up a DB to keep track of selections.

# UI Modification by MCP
- Allow an MCP to modify the UI.
  - Maybe the canvas area?
  - If MCP returns JSON with a special `custom_html` field, then inject this. [X]
    - Inject as a custom element or iframe? [X]
  - Could an MCP modify the callbacks?
    - Inject a custom prompt?

# Canvas Tool
- For the canvas tool, let the user adjust the width so it can take more or less of the screen compared to the chat UI.

