# MCP Server Session Management
- If a special `session_start` function exists, invoke it when a user first starts interacting with the server.
- Alternatively, inject some notion of session and user name in the tool calling, similar to the file setup.

# [X] File Return Handling
- If a file returned type is an image, or has field `custom_html`, then render in addition to allowing download. [X]

# [X]  MCP Marketplace & Selection
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

# [X ]Single line banners at the top
* this feature can be on or off via a .env file setting
* hit a url with custom api key that is form the .env file. also read the host name. 
* the route is {endpoint host}/banner 
* adn returns a json with a list of N banner messages. 
* The idea is taht the sys admin can quickly add a message at the top to show to users, ... like "Known outage on RAG server 5 detected at 1:36 pm Mountain Time. . ETA till restoration = 20 minutes"
* Similar to the RAG external url. Add a new folder called mocks/sys-admin-mock with a simple fastapi app that returns the needed json. 
* Each message should be on a new line, full width, 
* Do not cover any existing features, just stack below. 

mocking. 
* For the mocking, read a messages.txt in the same fodler as the mock folder. EAch line isa mesage. 
* use the fastapi Testclient similar to the RAG setup for now. 



# MCP for custom prompting. 

the design patter for the fastmcp is. The idea is that in the marketplace, you might mcps to expose some system prompt that is special, like "think like a finacial tech wizard. Identify market trends as you main objective" or "You are a expert dog trainer, try to explain each concept to dog user and dogs". 

probably in the handle_chat_message in the message-processor, if this is the first mesasge, then override the system prompt. 

Need to track different mcp services, like Tools, Resources, Templates, Prompts. 


"""
from fastmcp import FastMCP
from fastmcp.prompts.prompt import Message, PromptMessage, TextContent

mcp = FastMCP(name="PromptServer")

- Basic prompt returning a string (converted to user message automatically)
@mcp.prompt
def ask_about_topic(topic: str) -> str:
    """Generates a user message asking for an explanation of a topic."""
    return f"Can you please explain the concept of '{topic}'?"

- Prompt returning a specific message type
@mcp.prompt
def generate_code_request(language: str, task_description: str) -> PromptMessage:
    """Generates a user message requesting code generation."""
    content = f"Write a {language} function that performs the following task: {task_description}"
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
"""




# Update docs. 
* look at the project setup. 
* find all the .md files
* make a new folder called docs
* reoganize the docs into this folder. 
* the readme.md in the root shoudl be minimal and point to the docs 
* this app is getting complicated, so make sure there are multiple .md files in the docs folder. 
* try to use seperation of concerns, ... like a doc for the frontend, backend, mcp dev, quick developer dev, quick start, todo
---- this is not a hard rule, use your judgment. 
* an important considertion is when someone clones the code and wants to add new features, it takes a bit of time to see how things work. 
* be sure to note that we are using 'uv' as the python package manager. I've seen people ge this wrong a few tims. 


# write 10 unit tests
- these can be basic. 
- not integration test. 
- 10 for the backend
- 10 for the frontned. 


# Get user info, in a mcp server.
* The elicitation mechanism is intersting. 
* here for clients, ... this chat ui. 
https://gofastmcp.com/clients/elicitation
and for mcp servers. 
* https://gofastmcp.com/clients/elicitation


