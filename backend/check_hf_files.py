import os
from huggingface_hub import HfApi
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
token = os.environ.get('HF_TOKEN')
repo_id = "gour-himansh/AI"

api = HfApi(token=token)

files = api.list_repo_files(repo_id=repo_id, repo_type="space")
print("Files in HF Space:")
for f in files:
    print(f)
