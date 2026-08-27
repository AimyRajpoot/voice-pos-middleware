from app.schemas.pos import ProductSchema, CreateOrderRequest, OrderItemSchema
from app.schemas.command import VoiceCommandIntent, ExtractedEntity

# Validate a sample product
product = ProductSchema(
    id="101", 
    name="Zinger Burger", 
    price=400.0, 
    stock=20, 
    category="Burgers"
)

print("Schema Validation Success:", product.model_dump())