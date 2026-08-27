from app.nlp.normalizer import TextNormalizer

raw_voice_input = "I want two Zinger Burgers and a Coca-Cola!"
cleaned_output = TextNormalizer.normalize(raw_voice_input)

print("Raw Input:", raw_voice_input)
print("Normalized Output:", cleaned_output)