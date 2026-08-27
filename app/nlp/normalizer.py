import re

class TextNormalizer:
    NUMBER_MAP = {
        "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
        "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
        "a": "1", "an": "1"
    }

    @classmethod
    def normalize(cls, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        normalized_words = [cls.NUMBER_MAP.get(word, word) for word in words]
        return " ".join(normalized_words)