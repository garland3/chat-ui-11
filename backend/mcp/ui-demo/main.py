#!/usr/bin/env python3
"""
Demo MCP server that demonstrates custom UI capabilities.

This server shows how MCP servers can return responses with custom_html
fields to modify the UI.
"""

import json
import os
from typing import Dict, Any
from fastmcp import FastMCP


# Create the MCP server instance
mcp = FastMCP("UI Demo Server")

def load_template(template_name: str) -> str:
    """
    Load HTML template from templates directory.
    
    Args:
        template_name: Name of the template file to load
        
    Returns:
        The HTML content of the template
        
    Raises:
        FileNotFoundError: If the template file doesn't exist
    """
    template_path = os.path.join(os.path.dirname(__file__), "templates", template_name)
    with open(template_path, "r") as f:
        return f.read()

@mcp.tool
def create_button_demo() -> Dict[str, Any]:
    """
    Create a demo with custom HTML buttons that showcase UI modification capabilities.
    
    Returns:
        Dictionary with both regular content and custom HTML for UI injection
    """
    # Load the HTML template
    html_content = load_template("button_demo.html")
    
    # Convert to v2 MCP format with artifacts and display
    import base64
    html_base64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    
    return {
        "results": {
            "content": "Custom UI demo created successfully! Check the canvas panel for the interactive demo.",
            "success": True
        },
        "artifacts": [
            {
                "name": "ui_demo.html",
                "b64": html_base64,
                "mime": "text/html",
                "size": len(html_content.encode('utf-8')),
                "description": "Interactive UI demo with buttons and styling",
                "viewer": "html"
            }
        ],
        "display": {
            "open_canvas": True,
            "primary_file": "ui_demo.html",
            "mode": "replace",
            "viewer_hint": "html"
        }
    }

@mcp.tool
def create_data_visualization() -> Dict[str, Any]:
    """
    Create a simple data visualization using HTML and CSS.
    
    Returns:
        Dictionary with custom HTML containing a bar chart visualization
    """
    # Load the HTML template
    html_content = load_template("data_visualization.html")
    
    # Convert to v2 MCP format with artifacts and display
    import base64
    import datetime
    html_base64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    
    return {
        "results": {
            "content": "Data visualization created and displayed in the canvas panel.",
            "data_points": {
                "sales": 75,
                "satisfaction": 92,
                "market_share": 58
            }
        },
        "artifacts": [
            {
                "name": "data_visualization.html",
                "b64": html_base64,
                "mime": "text/html",
                "size": len(html_content.encode('utf-8')),
                "description": "Sales and customer satisfaction data visualization",
                "viewer": "html"
            }
        ],
        "display": {
            "open_canvas": True,
            "primary_file": "data_visualization.html",
            "mode": "replace",
            "viewer_hint": "html"
        },
        "meta_data": {
            "chart_type": "bar_chart",
            "data_points": 3,
            "metrics": ["sales", "satisfaction", "market_share"],
            "tool_execution": "create_data_visualization executed successfully",
            "timestamp": f"{datetime.datetime.now().isoformat()}"
        }
    }

@mcp.tool
def create_form_demo() -> Dict[str, Any]:
    """
    Create a demo form to show interactive UI capabilities.
    
    Returns:
        Dictionary with custom HTML containing an interactive form
    """
    # Load the HTML template
    html_content = load_template("form_demo.html")
    
    # Convert to v2 MCP format with artifacts and display
    import base64
    html_base64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    
    return {
        "results": {
            "content": "Interactive form demo created! You can interact with the form in the canvas panel.",
            "form_type": "demo"
        },
        "artifacts": [
            {
                "name": "interactive_form.html",
                "b64": html_base64,
                "mime": "text/html",
                "size": len(html_content.encode('utf-8')),
                "description": "Interactive form demo with input validation",
                "viewer": "html"
            }
        ],
        "display": {
            "open_canvas": True,
            "primary_file": "interactive_form.html",
            "mode": "replace",
            "viewer_hint": "html"
        },
        "meta_data": {
            "form_fields": ["name", "email", "message"],
            "interactive": True,
            "validation": "client_side"
        }
    }

@mcp.tool
def get_image() -> Dict[str, Any]:
    """
    Return the badmesh.png image from the ui-demo directory.
    
    Returns:
        Dictionary with the image data encoded in base64
    """
    # Get the path to the image file
    image_path = os.path.join(os.path.dirname(__file__), "badmesh.png")
    
    # Read the image file as binary
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    # Encode the image data in base64
    import base64
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # Return the image data with appropriate MIME type
    return {
        "results": {
            "content": "Image retrieved successfully!"
        },
        "artifacts": [
            {
                "name": "badmesh.png",
                "b64": image_base64,
                "mime": "image/png",
                "size": len(image_data),
                "description": "Bad mesh image for demonstration",
                "viewer": "image"
            }
        ],
        "display": {
            "open_canvas": True,
            "primary_file": "badmesh.png",
            "mode": "replace",
            "viewer_hint": "image"
        }
    }

if __name__ == "__main__":
    mcp.run()
