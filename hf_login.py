from huggingface_hub import login

token = input("Paste your HuggingFace token and press Enter: ").strip()
login(token=token)
print("\nDone! You can now run: python app.py")
