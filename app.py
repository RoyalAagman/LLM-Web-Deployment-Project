from flask import Flask, request, jsonify
import os
import sys
import logging
from dotenv import load_dotenv
import requests
import time

# Configure logging FIRST before anything else
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

logger.info("Starting Flask application initialization...")

# Initialize Flask app EARLY
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Your secret from the .env file
MY_SECRET = os.getenv('YOUR_SECRET')

# Verify environment variables exist
required_vars = ['YOUR_SECRET', 'GITHUB_TOKEN', 'GEMINI_API_KEY', 'GITHUB_USERNAME']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
    logger.error("Please ensure your .env file has all required variables")

logger.info("Loading local modules...")

# Import your modules with error handling
try:
    from llm_generator import generate_app_code
    logger.info("✓ llm_generator imported successfully")
except ImportError as e:
    logger.error(f"✗ Failed to import llm_generator: {str(e)}")
    logger.error("Make sure llm_generator.py exists and is in the same directory")
    # Don't exit - let Flask start so we can see error in logs

try:
    from github_manager import create_and_deploy_repo
    logger.info("✓ github_manager imported successfully")
except ImportError as e:
    logger.error(f"✗ Failed to import github_manager: {str(e)}")
    logger.error("Make sure github_manager.py exists and is in the same directory")
    # Don't exit - let Flask start so we can see error in logs

logger.info("Flask application initialized successfully")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway monitoring"""
    return jsonify({
        "status": "healthy",
        "service": "LLM Code Deployment System"
    }), 200


@app.route('/api-endpoint', methods=['POST'])
def handle_task():
    """
    This function handles incoming task requests.
    It's called when someone POSTs to your-server.com/api-endpoint
    """
    
    logger.info("Received request to /api-endpoint")
    
    # Step 1: Get the JSON data from the request
    try:
        data = request.get_json()
        if data is None:
            logger.error("No JSON data received")
            return jsonify({"error": "No JSON data provided"}), 400
        logger.info(f"Received data with task: {data.get('task')}")
    except Exception as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Step 2: Verify the secret (security check)
    provided_secret = data.get('secret')
    if provided_secret != MY_SECRET:
        logger.warning(f"Invalid secret provided")
        return jsonify({"error": "Invalid secret"}), 403
    
    logger.info("Secret validation passed")
    
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
        logger.info(f"Generating code for: {brief}")
        generated_files = generate_app_code(brief, attachments, checks)
        logger.info("Code generation completed")
        
        # Step 6: Create GitHub repo and deploy
        logger.info(f"Creating GitHub repo for task: {task_id}")
        repo_url, commit_sha, pages_url = create_and_deploy_repo(
            task_id, 
            generated_files, 
            brief
        )
        logger.info(f"Repository created: {repo_url}")
        
        # Step 7: Notify the evaluation server
        logger.info(f"Notifying evaluation server at: {evaluation_url}")
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
        
        logger.info(f"Successfully completed task {task_id}")
        
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {str(e)}", exc_info=True)
        # In production, you might want to notify the evaluation server of failure
    
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
            logger.info(f"Sending notification (attempt {attempt + 1}/{max_retries})")
            response = requests.post(
                eval_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Notification successful on attempt {attempt + 1}")
                return True
            else:
                logger.warning(f"Attempt {attempt + 1} failed with status {response.status_code}: {response.text}")
        
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
        
        # Wait before retrying (exponential backoff)
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1, 2, 4, 8 seconds
            logger.info(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    logger.error(f"Failed to notify evaluation server after {max_retries} attempts")
    return False


if __name__ == '__main__':
    # Get PORT from environment or default to 5000
    port = int(os.getenv('PORT', 5000))
    
    # Determine if we're in development or production
    is_production = os.getenv('FLASK_ENV') == 'production'
    
    logger.info(f"Starting Flask server on port {port}")
    logger.info(f"Environment: {'production' if is_production else 'development'}")
    
    # In production (Railway), use bind to 0.0.0.0
    # In development, can be localhost
    app.run(
        host='0.0.0.0',
        port=port,
        debug=not is_production,
        use_reloader=False  # Important for production
    )