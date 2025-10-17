from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from llm_generator import generate_app_code
from github_manager import create_and_deploy_repo
import requests
import time

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Your secret from the .env file
MY_SECRET = os.getenv('YOUR_SECRET')

@app.route('/api-endpoint', methods=['POST'])
def handle_task():
    """
    This function handles incoming task requests.
    It's called when someone POSTs to your-server.com/api-endpoint
    """
    
    # Step 1: Get the JSON data from the request
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Step 2: Verify the secret (security check)
    if data.get('secret') != MY_SECRET:
        return jsonify({"error": "Invalid secret"}), 403
    
    # Step 3: Extract task details
    email = data.get('email')
    task_id = data.get('task')
    round_num = data.get('round')
    nonce = data.get('nonce')
    brief = data.get('brief')
    checks = data.get('checks', [])
    evaluation_url = data.get('evaluation_url')
    attachments = data.get('attachments', [])
    
    # Step 4: Respond immediately with 200 OK
    # (We'll do the heavy work in the background)
    response = jsonify({
        "status": "received",
        "message": f"Processing task {task_id}, round {round_num}"
    })
    
    # Start processing in background (in real production, use Celery/Redis)
    # For simplicity, we'll do it synchronously here
    try:
        # Step 5: Generate code using LLM
        print(f"Generating code for: {brief}")
        generated_files = generate_app_code(brief, attachments, checks)
        
        # Step 6: Create GitHub repo and deploy
        print(f"Creating GitHub repo for task: {task_id}")
        repo_url, commit_sha, pages_url = create_and_deploy_repo(
            task_id, 
            generated_files, 
            brief
        )
        
        # Step 7: Notify the evaluation server
        print(f"Notifying evaluation server at: {evaluation_url}")
        notify_evaluation_server(
            evaluation_url,
            email,
            task_id,
            round_num,
            nonce,
            repo_url,
            commit_sha,
            pages_url
        )
        
        print(f"✅ Successfully completed task {task_id}")
        
    except Exception as e:
        print(f"❌ Error processing task: {str(e)}")
        # In production, you'd want better error handling
    
    return response, 200


def notify_evaluation_server(eval_url, email, task_id, round_num, nonce, 
                             repo_url, commit_sha, pages_url):
    """
    Sends repo details to the evaluation server.
    Implements retry logic with exponential backoff.
    """
    
    payload = {
        "email": email,
        "task": task_id,
        "round": round_num,
        "nonce": nonce,
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url
    }
    
    # Retry with exponential backoff: 1s, 2s, 4s, 8s
    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = requests.post(
                eval_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ Notification successful on attempt {attempt + 1}")
                return True
            else:
                print(f"⚠️ Attempt {attempt + 1} failed with status {response.status_code}")
        
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
        
        # Wait before retrying (exponential backoff)
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1, 2, 4, 8 seconds
            print(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    print(f"❌ Failed to notify evaluation server after {max_retries} attempts")
    return False


if __name__ == '__main__':
    # Run the Flask server
    # For testing locally on your Windows machine
    print("🚀 Starting API server...")
    print(f"Send POST requests to: http://localhost:5000/api-endpoint")
    app.run(host='0.0.0.0', port=5000, debug=True)