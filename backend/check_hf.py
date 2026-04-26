import os
from huggingface_hub import HfApi
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

token = os.environ.get('HF_TOKEN')
repo_id = "gour-himansh/AI"

api = HfApi(token=token)

try:
    runtime = api.get_space_runtime(repo_id=repo_id)
    print(f"Space Status: {runtime.stage}")
    
    print("\nAttempting to get hardware status and logs...")
    print(f"Hardware: {runtime.hardware}")
    
    # Try fetching via requests if huggingface_hub get_space_logs doesn't exist
    import requests
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://huggingface.co/api/spaces/{repo_id}/logs"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        logs = response.text.splitlines()
        print("\nLast 30 lines of logs:")
        for line in logs[-30:]:
            print(line)
    else:
        print(f"Failed to fetch logs: {response.status_code} - {response.text}")
        
except Exception as e:
    print(f"Error checking status: {e}")
