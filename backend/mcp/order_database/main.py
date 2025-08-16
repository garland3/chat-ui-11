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

if __name__ == "__main__":
    mcp.run()
