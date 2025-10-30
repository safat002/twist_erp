from huggingface_hub import snapshot_download

repo_id = "mistralai/Mistral-7B-Instruct-v0.1"

print(f"Downloading model: {repo_id}")
print("This will take a while and will download several gigabytes of data.")

snapshot_download(repo_id=repo_id, resume_download=True)

print("Model download complete.")
