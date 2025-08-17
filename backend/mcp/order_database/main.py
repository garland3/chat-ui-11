#!/usr/bin/env python3
"""
Order Database MCP Server using FastMCP
Provides customer order retrieval and status update functionality.
"""

from typing import Any, Dict, List
from fastmcp import FastMCP
from dataclasses import dataclass
from enum import Enum
import time
import os
import base64

# Initialize the MCP server
mcp = FastMCP("OrderDatabase")

class OrderStatus(Enum):
    SUBMITTED = "submitted"
    PACKAGED = "items-packaged"
    SHIPPED = "items-shipped"
    DELIVERED = "delivered"

@dataclass
class Order:
    order_number: str
    items: List[str]
    customer: str
    customer_address: str
    status: OrderStatus

# In-memory database (simulated)
ORDERS: Dict[str, Order] = {
    "ORD001": Order(
        order_number="ORD001",
        items=["Laptop", "Mouse", "Keyboard"],
        customer="John Doe",
        customer_address="123 Main St, Anytown, ST 12345",
        status=OrderStatus.SUBMITTED
    ),
    "ORD002": Order(
        order_number="ORD002",
        items=["Phone", "Case", "Charger"],
        customer="Jane Smith",
        customer_address="456 Oak Ave, Somewhere, ST 67890",
        status=OrderStatus.PACKAGED
    ),
    "ORD003": Order(
        order_number="ORD003",
        items=["Tablet", "Stylus"],
        customer="Bob Johnson",
        customer_address="789 Pine Rd, Elsewhere, ST 54321",
        status=OrderStatus.SHIPPED
    )
}

def _finalize_meta(meta: Dict[str, Any], start: float) -> Dict[str, Any]:
    """Attach timing info and return meta_data dict."""
    meta = dict(meta)  # shallow copy
    meta["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 3)
    return meta

@mcp.tool
def get_order(order_number: str) -> Dict[str, Any]:
    """
    Retrieve a customer order by order number.
    
    Args:
        order_number: The order number to retrieve
        
    Returns:
        Dictionary with order details or error message
    """
    start = time.perf_counter()
    meta: Dict[str, Any] = {}
    
    try:
        if order_number not in ORDERS:
            meta.update({"is_error": True, "reason": "not_found"})
            return {
                "results": {"error": f"Order {order_number} not found"},
                "meta_data": _finalize_meta(meta, start)
            }
        
        order = ORDERS[order_number]
        meta.update({"is_error": False})
        return {
            "results": {
                "order_number": order.order_number,
                "items": order.items,
                "customer": order.customer,
                "customer_address": order.customer_address,
                "status": order.status.value
            },
            "meta_data": _finalize_meta(meta, start)
        }
    except Exception as e:
        meta.update({"is_error": True, "reason": type(e).__name__})
        return {
            "results": {"error": f"Error retrieving order: {str(e)}"},
            "meta_data": _finalize_meta(meta, start)
        }

@mcp.tool
def update_order_status(order_number: str, new_status: str) -> Dict[str, Any]:
    """
    Update the status of a customer order.
    
    Args:
        order_number: The order number to update
        new_status: The new status (submitted, items-packaged, items-shipped, delivered)
        
    Returns:
        Dictionary with success status or error message
    """
    start = time.perf_counter()
    meta: Dict[str, Any] = {}
    
    try:
        if order_number not in ORDERS:
            meta.update({"is_error": True, "reason": "not_found"})
            return {
                "results": {"error": f"Order {order_number} not found"},
                "meta_data": _finalize_meta(meta, start)
            }
        
        # Validate status
        try:
            status_enum = OrderStatus(new_status)
        except ValueError:
            valid_statuses = [status.value for status in OrderStatus]
            meta.update({"is_error": True, "reason": "invalid_status"})
            return {
                "results": {
                    "error": f"Invalid status: {new_status}",
                    "valid_statuses": valid_statuses
                },
                "meta_data": _finalize_meta(meta, start)
            }
        
        # Update order status
        ORDERS[order_number].status = status_enum
        meta.update({"is_error": False})
        return {
            "results": {
                "success": True,
                "order_number": order_number,
                "new_status": new_status
            },
            "meta_data": _finalize_meta(meta, start)
        }
    except Exception as e:
        meta.update({"is_error": True, "reason": type(e).__name__})
        return {
            "results": {"error": f"Error updating order status: {str(e)}"},
            "meta_data": _finalize_meta(meta, start)
        }

@mcp.tool
def list_all_orders() -> Dict[str, Any]:
    """
    List all customer orders with their basic information.
    
    Returns:
        Dictionary with list of all orders
    """
    start = time.perf_counter()
    meta: Dict[str, Any] = {}
    
    try:
        orders_list = []
        for order in ORDERS.values():
            orders_list.append({
                "order_number": order.order_number,
                "customer": order.customer,
                "status": order.status.value,
                "item_count": len(order.items)
            })
        
        meta.update({"is_error": False})
        return {
            "results": {
                "orders": orders_list,
                "total_count": len(orders_list)
            },
            "meta_data": _finalize_meta(meta, start)
        }
    except Exception as e:
        meta.update({"is_error": True, "reason": type(e).__name__})
        return {
            "results": {"error": f"Error listing orders: {str(e)}"},
            "meta_data": _finalize_meta(meta, start)
        }

@mcp.tool
def get_signal_data_csv() -> Dict[str, Any]:
    """
    Return the signal_data.csv file from the same directory as this MCP.
    
    Returns:
        Dictionary with the CSV file as a base64 encoded artifact
    """
    start = time.perf_counter()
    meta: Dict[str, Any] = {}
    
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, "signal_data.csv")
        
        if not os.path.exists(csv_path):
            meta.update({"is_error": True, "reason": "file_not_found"})
            return {
                "results": {"error": "signal_data.csv file not found"},
                "meta_data": _finalize_meta(meta, start)
            }
        
        # Read the CSV file
        with open(csv_path, 'rb') as f:
            csv_content = f.read()
        
        # Encode as base64
        csv_b64 = base64.b64encode(csv_content).decode('utf-8')
        
        meta.update({"is_error": False, "file_size_bytes": len(csv_content)})
        return {
            "results": {
                "message": "Signal data CSV file retrieved successfully",
                "filename": "signal_data.csv",
                "file_size_bytes": len(csv_content)
            },
            "artifacts": [
                {
                    "name": "signal_data.csv",
                    "b64": csv_b64,
                    "mime": "text/csv",
                }
            ],
            "display": {
                "open_canvas": True,
                "primary_file": "signal_data.csv",
                "mode": "replace",
                "viewer_hint": "code",
            },
            "meta_data": _finalize_meta(meta, start)
        }
    except Exception as e:
        meta.update({"is_error": True, "reason": type(e).__name__})
        return {
            "results": {"error": f"Error reading CSV file: {str(e)}"},
            "meta_data": _finalize_meta(meta, start)
        }

if __name__ == "__main__":
    mcp.run()
