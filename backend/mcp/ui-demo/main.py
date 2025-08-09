#!/usr/bin/env python3
"""
Demo MCP server that demonstrates custom UI capabilities.

This server shows how MCP servers can return responses with custom_html
fields to modify the UI.
"""

import json
from typing import Dict, Any
from fastmcp import FastMCP


# Common template for custom UI demos
COMMON_UI_TEMPLATE = """
<div style=\"background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 28px 32px; 
            border-radius: 14px; 
            color: white; 
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 32px auto;\">
    {content}
</div>
"""

# Create the MCP server instance
mcp = FastMCP("UI Demo Server")

@mcp.tool
def create_button_demo() -> Dict[str, Any]:
    """
    Create a demo with custom HTML buttons that showcase UI modification capabilities.
    
    Returns:
        Dictionary with both regular content and custom HTML for UI injection
    """
    demo_content = """
        <h2 style=\"margin-top: 0;\">🎨 Custom UI Demo</h2>
        <p>This content was injected by an MCP server using the custom_html field!</p>
        <div style=\"display: flex; gap: 10px; margin-top: 15px;\">
            <button onclick=\"alert('Hello from MCP!')\" 
                    style=\"background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;\">
                Click Me!
            </button>
            <button onclick=\"document.getElementById('demo-text').style.color = 'yellow'\" 
                    style=\"background: #ff9800; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;\">
                Change Text Color
            </button>
        </div>
        <p id=\"demo-text\" style=\"margin-top: 15px; font-size: 16px;\">
            This text can be modified by the button above!
        </p>
        <div style=\"margin-top: 20px; padding: 10px; background: rgba(255,255,255,0.2); border-radius: 5px;\">
            <strong>Capabilities Demonstrated:</strong>
            <ul style=\"margin: 10px 0; padding-left: 20px;\">
                <li>Custom HTML injection</li>
                <li>Interactive JavaScript buttons</li>
                <li>Dynamic styling</li>
                <li>Safe HTML sanitization</li>
            </ul>
        </div>
    """
    custom_html = COMMON_UI_TEMPLATE.replace("{content}", demo_content)
    
    # Save HTML to file instead of returning custom_html
    import base64
    html_base64 = base64.b64encode(custom_html.encode('utf-8')).decode('utf-8')
    
    return {
        "content": "Custom UI demo created successfully! Check the canvas panel for the interactive demo.",
        "success": True,
        "returned_files": [{
            "filename": "ui_demo.html",
            "content_base64": html_base64
        }]
    }

@mcp.tool
def create_data_visualization() -> Dict[str, Any]:
    """
    Create a simple data visualization using HTML and CSS.
    
    Returns:
        Dictionary with custom HTML containing a bar chart visualization
    """
    demo_content = """
        <h3 style=\"text-align: center; margin-top: 0; color: #63b3ed;\">📊 Sample Data Visualization</h3>
        <div style=\"margin: 20px 0;\">
            <div style=\"margin-bottom: 10px;\">
                <span style=\"color: #a0aec0;\">Sales (Jan-Mar 2024)</span>
                <div style=\"background: #1a202c; height: 30px; border-radius: 15px; position: relative; margin-top: 5px;\">
                    <div style=\"background: linear-gradient(90deg, #4299e1, #63b3ed); height: 100%; width: 75%; border-radius: 15px; display: flex; align-items: center; justify-content: center; font-weight: bold;\">75%</div>
                </div>
            </div>
            <div style=\"margin-bottom: 10px;\">
                <span style=\"color: #a0aec0;\">Customer Satisfaction</span>
                <div style=\"background: #1a202c; height: 30px; border-radius: 15px; position: relative; margin-top: 5px;\">
                    <div style=\"background: linear-gradient(90deg, #48bb78, #68d391); height: 100%; width: 92%; border-radius: 15px; display: flex; align-items: center; justify-content: center; font-weight: bold;\">92%</div>
                </div>
            </div>
            <div style=\"margin-bottom: 10px;\">
                <span style=\"color: #a0aec0;\">Market Share</span>
                <div style=\"background: #1a202c; height: 30px; border-radius: 15px; position: relative; margin-top: 5px;\">
                    <div style=\"background: linear-gradient(90deg, #ed8936, #f6ad55); height: 100%; width: 58%; border-radius: 15px; display: flex; align-items: center; justify-content: center; font-weight: bold;\">58%</div>
                </div>
            </div>
        </div>
        <div style=\"text-align: center; margin-top: 20px; padding: 10px; background: rgba(99, 179, 237, 0.1); border-radius: 5px;\">
            <small style=\"color: #a0aec0;\">Generated by MCP Server with custom HTML</small>
        </div>
    """
    custom_html = COMMON_UI_TEMPLATE.replace("{content}", demo_content)
    
    # Save HTML to file instead of returning custom_html
    import base64
    html_base64 = base64.b64encode(custom_html.encode('utf-8')).decode('utf-8')
    
    return {
        "content": "Data visualization created and displayed in the canvas panel.",
        "data_points": {
            "sales": 75,
            "satisfaction": 92,
            "market_share": 58
        },
        "returned_files": [{
            "filename": "data_visualization.html",
            "content_base64": html_base64
        }]
    }

@mcp.tool
def create_form_demo() -> Dict[str, Any]:
    """
    Create a demo form to show interactive UI capabilities.
    
    Returns:
        Dictionary with custom HTML containing an interactive form
    """
    demo_content = """
        <h3 style=\"color: #63b3ed; margin-top: 0; text-align: center;\">📋 Interactive Form Demo</h3>
        <form onsubmit=\"event.preventDefault(); alert('Form submitted! Data: ' + JSON.stringify({name: this.name.value, email: this.email.value, message: this.message.value}));\" style=\"display: flex; flex-direction: column; gap: 15px;\">
            <div>
                <label style=\"display: block; color: #a0aec0; margin-bottom: 5px;\">Name:</label>
                <input type=\"text\" name=\"name\" style=\"width: 100%; padding: 8px 12px; border: 1px solid #4a5568; border-radius: 6px; background: #2d3748; color: white; box-sizing: border-box;\" placeholder=\"Enter your name\" />
            </div>
            <div>
                <label style=\"display: block; color: #a0aec0; margin-bottom: 5px;\">Email:</label>
                <input type=\"email\" name=\"email\" style=\"width: 100%; padding: 8px 12px; border: 1px solid #4a5568; border-radius: 6px; background: #2d3748; color: white; box-sizing: border-box;\" placeholder=\"Enter your email\" />
            </div>
            <div>
                <label style=\"display: block; color: #a0aec0; margin-bottom: 5px;\">Message:</label>
                <textarea name=\"message\" rows=\"4\" style=\"width: 100%; padding: 8px 12px; border: 1px solid #4a5568; border-radius: 6px; background: #2d3748; color: white; resize: vertical; box-sizing: border-box;\" placeholder=\"Enter your message\"></textarea>
            </div>
            <button type=\"submit\" style=\"background: linear-gradient(45deg, #667eea, #764ba2); color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: bold; transition: transform 0.2s;\" onmouseover=\"this.style.transform='scale(1.05)'\" onmouseout=\"this.style.transform='scale(1)'\">Submit Form</button>
        </form>
        <div style=\"margin-top: 20px; padding: 15px; background: rgba(72, 187, 120, 0.1); border-radius: 6px; border-left: 4px solid #48bb78;\">
            <strong style=\"color: #68d391;\">Note:</strong> 
            <span style=\"color: #a0aec0;\">This form demonstrates how MCP servers can create interactive UI elements. Form submission shows an alert with the entered data.</span>
        </div>
    """
    custom_html = COMMON_UI_TEMPLATE.replace("{content}", demo_content)
    
    # Save HTML to file instead of returning custom_html
    import base64
    html_base64 = base64.b64encode(custom_html.encode('utf-8')).decode('utf-8')
    
    return {
        "content": "Interactive form demo created! You can interact with the form in the canvas panel.",
        "form_type": "demo",
        "returned_files": [{
            "filename": "interactive_form.html",
            "content_base64": html_base64
        }]
    }

if __name__ == "__main__":
    mcp.run()