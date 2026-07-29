from google import genai

client = genai.Client(api_key="AQ.Ab8RN6J0ApQGXHDjK6gSIeSTmFoQ0OuFaCLActsajtgaYH234A")

for m in client.models.list():
    print(m.name)