from pydantic import BaseModel, Field
from typing import Optional

class ProductSchema(BaseModel):
    id: str
    name: str
    price: float
    stock: int
    category: Optional[str] = None

class OrderItemSchema(BaseModel):
    product_id: str
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")

class CreateOrderRequest(BaseModel):
    items: list[OrderItemSchema]

class OrderResponseSchema(BaseModel):
    order_id: str
    items: list[OrderItemSchema]
    total_price: float
    status: str