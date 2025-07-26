import google.generativeai as genai

genai.configure(api_key="AIzaSyAMGyvbj5VpkBm5fNKm2PyW6yioSk-zyZM")

models = genai.list_models()
print("Available models:")
for m in models:
    print(f"- {m.name} (supports: {m.supported_generation_methods})")