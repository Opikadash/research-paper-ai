from google import genai

client = genai.Client(api_key="AIzaSyCSws7EPx_55IC_JHWBRgDt9TMpXRWvHKk")

# Print all available models
for model in client.models.list():
    print(model.name)
