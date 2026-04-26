import os
from huggingface_hub import hf_hub_download
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
token = os.environ.get('HF_TOKEN')
repo_id = "gour-himansh/AI"

path = hf_hub_download(repo_id=repo_id, repo_type="space", filename="Dockerfile", token=token)
with open(path, "r") as f:
    print(f.read())
