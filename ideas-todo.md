# MCP Server Session Management
- If a special `session_start` function exists, invoke it when a user first starts interacting with the server.
- Alternatively, inject some notion of session and user name in the tool calling, similar to the file setup.

# [X] File Return Handling
- If a file returned type is an image, or has field `custom_html`, then render in addition to allowing download. [X]

# MCP Marketplace & Selection
- Create a different route `/marketplace`.
  - Show different possible MCPs, allow selecting, then on the main UI, only show the user-selected MCP.
  - Would need to set up a DB to keep track of selections.
  --- proably not for now. we can just save to browswer memory similar to now. 
  - a future todo woudl be to get more info about each mcp, like ratings, or downlaods
  - again only show the authorized mcps, this is alrady done and is good. 
  - the markpalce shows the servers you could use. then youc an select a server witih a checkbox. 
  - on the / route for the Tools and Integratiosn panel. only show the selected servers. 

# [X] UI Modification by MCP
- Allow an MCP to modify the UI. [X]
  - Maybe the canvas area? [X]
  - If MCP returns JSON with a special `custom_html` field, then inject this. [X]
    - Inject as a custom element or iframe? [X]
  - Could an MCP modify the callbacks?
    - Inject a custom prompt?

# [X] Canvas Tool
- For the canvas tool, let the user adjust the width so it can take more or less of the screen compared to the chat UI. [X]


# MCP server fix. 
* currently for mcp serves, they need to be in the mcp folder with the same fodler name as the mcp folder. 
* the todo, is to make it properly use the "command" in the mcp.json, so the path to the mcp server can be whatever. 
* enable http mcp servers, ... for connect to a remote mcp server. 

# Single line banners at the top
* this feature can be on or off via a .env file setting
* hit a url with custom api key that is form the .env file. also read the host name. 
* the route is {endpoint host}/banner 
* adn returns a json with a list of N banner messages. 
* The idea is taht the sys admin can quickly add a message at the top to show to users, ... like "Known outage on RAG server 5. ETA = 20 minutes"
* Similar to the RAG external url. Add a new folder called sys-admin-mock with a simple fastapi app that lets returns the needed json. 
* Each message should be on a new line, full width, 
* Do not cover any existing features, just stack below. 