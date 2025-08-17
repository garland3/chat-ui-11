"""
PowerPoint Generator MCP Server using FastMCP.

Converts JSON input containing slide data into a PowerPoint presentation.
Input should be a JSON object with a 'slides' array, each containing 'title' and 'content' fields.
Supports bullet point lists in content for more complex slide formatting.

Tools:
 - json_to_pptx: Converts JSON input to PowerPoint presentation

Demonstrates: JSON input handling, file output with base64 encoding, and structured output.
"""

from __future__ import annotations

import base64
import os
import tempfile
from typing import Any, Dict, List, Annotated, Optional
from fastmcp import FastMCP
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pdfkit import from_string


mcp = FastMCP("pptx_generator")


@mcp.tool
def json_to_pptx(
    input_data: Annotated[str, "JSON string containing slide data in this format: {\"slides\": [{\"title\": \"Slide 1\", \"content\": \"- Item 1\\n- Item 2\\n- Item 3\"}, {\"title\": \"Slide 2\", \"content\": \"- Item A\\n- Item B\"}]}"]
) -> Dict[str, Any]:
    """
    Converts JSON input to PowerPoint presentation with support for bullet point lists
    
    Args:
        input_data: JSON string containing slide data in this format:
            {"slides": [
                {"title": "Slide 1", "content": "- Item 1\\n- Item 2\\n- Item 3"},
                {"title": "Slide 2", "content": "- Item A\\n- Item B"}
            ]}
    
    Returns:
        Dictionary with 'results' and 'artifacts' keys:
        - 'results': Success message or error message
        - 'artifacts': List of artifact dictionaries with 'name', 'b64', and 'mime' keys
    """
    print("Starting json_to_pptx execution...")
    try:
        import json
        data = json.loads(input_data)
        
        if not isinstance(data, dict) or 'slides' not in data:
            return {"results": {"error": "Input must be a JSON object containing 'slides' array"}}
            
        slides = data['slides']
        print(f"Processing {len(slides)} slides...")
        
        # Create presentation
        prs = Presentation()
        print("Created PowerPoint presentation object")
        
        for i, slide in enumerate(slides):
            title = slide.get('title', 'Untitled Slide')
            content = slide.get('content', '')
            
            # Add slide
            slide_layout = prs.slide_layouts[1]  # Title and content layout
            slide_obj = prs.slides.add_slide(slide_layout)
            
            # Add title
            title_shape = slide_obj.shapes.title
            title_shape.text = title
            print(f"Added slide {i+1}: {title}")
            
            # Add content
            body_shape = slide_obj.placeholders[1]
            tf = body_shape.text_frame
            tf.text = ""
            
            # Set text alignment to left
            tf.paragraphs[0].alignment = PP_ALIGN.LEFT
            
            # Process bullet points if content contains them
            if content.strip() and content.strip().startswith('-'):
                # Split by newline and process each line
                items = [item.strip() for item in content.split('\n') if item.strip()]
                print(f"Slide {i+1} has {len(items)} bullet points")
                for item in items:
                    if item.startswith('-'):
                        item_text = item[1:].strip()  # Remove the dash
                        p = tf.add_paragraph()
                        p.text = item_text
                        p.level = 0
                        p.font.size = Pt(24)
                        p.space_after = Pt(6)
                        p.alignment = PP_ALIGN.LEFT
            else:
                # Handle regular text without bullet points
                p = tf.add_paragraph()
                p.text = content
                p.font.size = Pt(24)
                p.space_after = Pt(6)
                p.alignment = PP_ALIGN.LEFT
            
            # Add paragraph with 24pt font size
            p = tf.add_paragraph()
            p.text = "Additional content paragraph"
            p.font.size = Pt(24)
            p.space_after = Pt(6)
            p.alignment = PP_ALIGN.LEFT
            
        # Save presentation
        pptx_output_path = os.path.join(os.getcwd(), "output_presentation.pptx")
        prs.save(pptx_output_path)
        print(f"Saved PowerPoint presentation to {pptx_output_path}")
        
        # Convert to PDF using pdfkit
        pdf_output_path = os.path.join(os.getcwd(), "output_presentation.pdf")
        print(f"Starting PDF conversion to {pdf_output_path}")
        
        # Create HTML representation of the presentation
        html_content = "<html><head><title>PowerPoint Presentation</title></head><body>"
        
        for i, slide in enumerate(slides):
            title = slide.get('title', 'Untitled Slide')
            content = slide.get('content', '')
            
            html_content += f"<div style='margin-bottom: 20px; border: 1px solid #ddd; padding: 10px; border-radius: 4px;'><h2 style='color: #2c3e50; margin-bottom: 10px;'>{title}</h2>"
            
            if content.strip() and content.strip().startswith('-'):
                items = [item.strip() for item in content.split('\n') if item.strip()]
                html_content += "<ul style='margin: 0; padding-left: 20px;'>"
                for item in items:
                    if item.startswith('-'):
                        item_text = item[1:].strip()
                        html_content += f"<li style='margin-bottom: 5px; font-size: 18px;'>{item_text}</li>"
                html_content += "</ul>"
            else:
                html_content += f"<p style='margin: 0; font-size: 18px;'>{content}</p>"
            
            html_content += "</div>"
        
        html_content += "</body></html>"
        
        # Generate PDF from HTML
        try:
            print("Converting HTML to PDF...")
            from_string(html_content, pdf_output_path, options={"page-size": "A4", "margin-top": "0.75in", "margin-right": "0.75in", "margin-bottom": "0.75in", "margin-left": "0.75in"})
            print(f"PDF successfully created at {pdf_output_path}")
        except Exception as e:
            # If pdfkit fails, return only PPTX
            print(f"Warning: PDF conversion failed: {str(e)}")
            # Remove the PDF file if it exists
            if os.path.exists(pdf_output_path):
                os.remove(pdf_output_path)
            print("PDF file removed due to conversion error")
        
        # Read PPTX file as bytes
        with open(pptx_output_path, "rb") as f:
            pptx_bytes = f.read()
            
        # Encode PPTX as base64
        pptx_b64 = base64.b64encode(pptx_bytes).decode('utf-8')
        print("PPTX file successfully encoded to base64")
        
        # Read PDF file as bytes if it exists
        pdf_b64 = None
        if os.path.exists(pdf_output_path):
            with open(pdf_output_path, "rb") as f:
                pdf_bytes = f.read()
            pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
            print("PDF file successfully encoded to base64")
        
        # Prepare artifacts
        artifacts = [
            {
                "name": "presentation.pptx",
                "b64": pptx_b64,
                "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            }
        ]
        
        # Add PDF if conversion was successful
        if pdf_b64:
            artifacts.append({
                "name": "presentation.pdf",
                "b64": pdf_b64,
                "mime": "application/pdf",
            })
            print(f"Added {len(artifacts)} artifacts to response")
        else:
            print("No PDF artifact added due to conversion failure")
        
        return {
            "results": {
                "operation": "json_to_pptx",
                "message": "PowerPoint presentation generated successfully.",
                "pdf_generated": pdf_b64 is not None,
            },
            "artifacts": artifacts,
            "display": {
                "open_canvas": True,
                "primary_file": "presentation.pptx",
                "mode": "replace",
                "viewer_hint": "powerpoint",
            },
            "meta_data": {
                "generated_slides": len(slides),
                "output_files": [f"presentation.pptx", "presentation.pdf"] if pdf_b64 else ["presentation.pptx"],
                "output_file_paths": [pptx_output_path, pdf_output_path] if pdf_b64 else [pptx_output_path],
            },
        }
    except Exception as e:
        print(f"Error in json_to_pptx: {str(e)}")
        return {"results": {"error": f"Error creating PowerPoint: {str(e)}"}}


if __name__ == "__main__":
    mcp.run()
