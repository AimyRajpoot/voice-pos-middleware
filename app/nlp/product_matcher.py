from thefuzz import process
from app.schemas.pos import ProductSchema

class ProductMatcher:
    def __init__(self, catalog: list[ProductSchema]):
        self.catalog = catalog
        # Map product names to their ProductSchema objects
        self.name_to_product = {p.name.lower(): p for p in catalog}

    def match_product(self, query: str, score_threshold: int = 60) -> tuple[ProductSchema | None, int]:
        """
        Matches a raw string (e.g. 'zinger') against the catalog product names.
        Returns a tuple: (ProductSchema, confidence_score)
        """
        choices = list(self.name_to_product.keys())
        if not choices:
            return None, 0

        # Find best match using fuzzy token set ratio
        best_match, score = process.extractOne(query.lower(), choices)
        
        if score >= score_threshold:
            matched_product = self.name_to_product[best_match]
            return matched_product, score
            
        return None, score