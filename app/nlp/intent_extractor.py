import re
from app.nlp.normalizer import TextNormalizer
from app.nlp.product_matcher import ProductMatcher
from app.schemas.command import VoiceCommandIntent, ExtractedEntity

class IntentExtractor:
    def __init__(self, product_matcher: ProductMatcher):
        self.matcher = product_matcher

    def parse_command(self, raw_text: str) -> VoiceCommandIntent:
        normalized_text = TextNormalizer.normalize(raw_text)
        
        # Remove action trigger words from the beginning
        clean_text = re.sub(r'^(add|order|get|buy|please)\s+', '', normalized_text)
        
        entities = []
        segments = re.split(r'\band\b|,', clean_text)

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            # Extract number anywhere at the start of the item phrase
            match = re.match(r'^(\d+)\s+(.+)$', segment)
            if match:
                quantity = int(match.group(1))
                item_text = match.group(2)
            else:
                quantity = 1
                item_text = segment

            matched_product, score = self.matcher.match_product(item_text)

            entity = ExtractedEntity(
                raw_text=item_text,
                matched_product_id=matched_product.id if matched_product else None,
                quantity=quantity,
                confidence_score=float(score)
            )
            entities.append(entity)

        return VoiceCommandIntent(
            intent_type="ADD_TO_ORDER",
            entities=entities,
            original_transcript=raw_text
        )
    