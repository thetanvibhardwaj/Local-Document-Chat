from google import genai

client = genai.Client(api_key="AQ.Ab8RN6J0ApQGXHDjK6gSIeSTmFoQ0OuFaCLActsajtgaYH234A")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Hello"
)

print(response.text)