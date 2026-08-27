from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .data import products, orders


app = FastAPI(
    title="Mock Restaurant POS",
    description="Temporary POS API for Voice-to-POS Middleware",
    version="1.0.0"
)


class OrderItem(BaseModel):
    product_id: str
    quantity: int


class CreateOrderRequest(BaseModel):
    items: list[OrderItem]


@app.get("/")
def root():
    return {
        "message": "Mock POS is running"
    }


@app.get("/products")
def get_products():
    return products


@app.get("/products/{product_id}")
def get_product(product_id: str):

    for product in products:
        if product["id"] == product_id:
            return product

    raise HTTPException(
        status_code=404,
        detail="Product not found"
    )


@app.get("/products/{product_id}/stock")
def get_stock(product_id: str):

    for product in products:
        if product["id"] == product_id:
            return {
                "product_id": product_id,
                "product_name": product["name"],
                "stock": product["stock"]
            }

    raise HTTPException(
        status_code=404,
        detail="Product not found"
    )


@app.post("/orders")
def create_order(request: CreateOrderRequest):

    total = 0
    order_items = []

    for item in request.items:

        product = next(
            (p for p in products if p["id"] == item.product_id),
            None
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

        if item.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="Quantity must be greater than zero"
            )

        if item.quantity > product["stock"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Only {product['stock']} units of "
                    f"{product['name']} are available"
                )
            )

        item_total = product["price"] * item.quantity
        total += item_total

        order_items.append({
            "product_id": product["id"],
            "product_name": product["name"],
            "quantity": item.quantity,
            "unit_price": product["price"],
            "total": item_total
        })

    # Reduce stock only after validation succeeds
    for item in request.items:
        product = next(
            p for p in products if p["id"] == item.product_id
        )
        product["stock"] -= item.quantity

    order = {
        "order_id": f"ORD-{len(orders) + 1001}",
        "items": order_items,
        "total": total,
        "status": "created"
    }

    orders.append(order)

    return order


@app.get("/orders/{order_id}")
def get_order(order_id: str):

    for order in orders:
        if order["order_id"] == order_id:
            return order

    raise HTTPException(
        status_code=404,
        detail="Order not found"
    )