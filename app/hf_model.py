from dotenv import load_dotenv
import os
import requests

load_dotenv()

API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"
headers = {
    "Authorization": f"Bearer {os.environ['HF_TOKEN']}",
}

def query(text:str,categories: list[str]):
    payload={
        "inputs": text,
        "parameters": {
            "candidate_labels": categories
        }
    }
    response = requests.post(API_URL, headers=headers, json=payload)
 
    if response.status_code != 200:
        raise Exception(f"HF API error: {response.text}")
    result=response.json()
    print("HuggingFace API Response:")
    print(f"Type: {type(result)}")
    print(f"Content: {result}")
    return result

# query("machine learning",["technology","legal"])