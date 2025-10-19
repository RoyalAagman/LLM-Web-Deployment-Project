from flask import Flask, request, jsonify
import os
import sys
import logging

# Setup logging to stdout immediately
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, force=True)
logger = logging.getLogger(__name__)

print("STARTING APP INITIALIZATION", flush=True)
sys.stdout.flush()

from dotenv import load_dotenv
load_dotenv()

print("LOADED ENV VARS", flush=True)
sys.stdout.flush()

app = Flask(__name__)

MY_SECRET = os.getenv('YOUR_SECRET')
print(f"SECRET LOADED: {bool(MY_SECRET)}", flush=True)
sys.stdout.flush()

# Test imports one by one
print("IMPORTING llm_generator...", flush=True)
sys.stdout.flush()
try:
    from llm_generator import generate_app_code
    print("SUCCESS: llm_generator imported", flush=True)
except Exception as e:
    print(f"ERROR importing llm_generator: {e}", flush=True)
    sys.stdout.flush()

print("IMPORTING github_manager...", flush=True)
sys.stdout.flush()
try:
    from github_manager import create_and_deploy_repo
    print("SUCCESS: github_manager imported", flush=True)
except Exception as e:
    print(f"ERROR importing github_manager: {e}", flush=True)
    sys.stdout.flush()

import requests
import time

print("APP INITIALIZATION COMPLETE", flush=True)
sys.stdout.flush()


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200


@app.route('/api-endpoint', methods=['POST'])
def handle_task():
    print("RECEIVED REQUEST", flush=True)
    sys.stdout.flush()
    
    try:
        data = request.get_json()
        print(f"JSON PARSED: {data.get('task')}", flush=True)
        sys.stdout.flush()
        
        if data.get('secret') != MY_SECRET:
            print("INVALID SECRET", flush=True)
            sys.stdout.flush()
            return jsonify({"error": "Invalid secret"}), 403
        
        print("SECRET VALID", flush=True)
        sys.stdout.flush()
        
        task_id = data.get('task')
        brief = data.get('brief')
        checks = data.get('checks', [])
        attachments = data.get('attachments', [])
        
        print(f"GENERATING CODE FOR: {task_id}", flush=True)
        sys.stdout.flush()
        
        generated_files = generate_app_code(brief, attachments, checks)
        print(f"CODE GENERATED: {list(generated_files.keys())}", flush=True)
        sys.stdout.flush()
        
        print(f"CREATING REPO: {task_id}", flush=True)
        sys.stdout.flush()
        
        repo_url, commit_sha, pages_url = create_and_deploy_repo(task_id, generated_files, brief)
        print(f"REPO CREATED: {repo_url}", flush=True)
        sys.stdout.flush()
        
        return jsonify({
            "status": "success",
            "repo_url": repo_url,
            "pages_url": pages_url
        }), 200
        
    except Exception as e:
        print(f"ERROR: {str(e)}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        sys.stdout.flush()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"STARTING SERVER ON PORT {port}", flush=True)
    sys.stdout.flush()
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)