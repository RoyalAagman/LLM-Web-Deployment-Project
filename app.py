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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# Ensure logging is flushed
import atexit
def close_logging():
    for handler in logging.root.handlers[:]:
        handler.close()
atexit.register(close_logging)

# Load environment variables from .env file
load_dotenv()

logger.info("="*80)
logger.info("Starting Flask application initialization...")
logger.info("="*80)

# Initialize Flask app EARLY
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Your secret from the .env file
MY_SECRET = os.getenv('YOUR_SECRET')

# Verify environment variables exist
required_vars = ['YOUR_SECRET', 'GITHUB_TOKEN', 'GEMINI_API_KEY', 'GITHUB_USERNAME']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    logger.error(f"CRITICAL: Missing environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

logger.info("Loading local modules...")

# Import your modules with error handling
try:
    from llm_generator import generate_app_code
    logger.info("✓ llm_generator imported successfully")
except ImportError as e:
    logger.error(f"✗ Failed to import llm_generator: {str(e)}", exc_info=True)
    sys.exit(1)

try:
    from github_manager import create_and_deploy_repo
    logger.info("✓ github_manager imported successfully")
except ImportError as e:
    logger.error(f"✗ Failed to import github_manager: {str(e)}", exc_info=True)
    sys.exit(1)

logger.info("="*80)
logger.info("Flask application initialized successfully")
logger.info("="*80)


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
    Processes synchronously to catch and log all errors.
    """
    
    logger.info("="*80)
    logger.info("RECEIVED NEW REQUEST TO /api-endpoint")
    logger.info("="*80)
    
    # Step 1: Get the JSON data from the request
    try:
        data = request.get_json()
        if data is None:
            logger.error("No JSON data received")
            return jsonify({"error": "No JSON data provided"}), 400
        logger.info(f"Received data with task: {data.get('task')}")
    except Exception as e:
        logger.error(f"Failed to parse JSON: {str(e)}", exc_info=True)
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Step 2: Verify the secret (security check)
    provided_secret = data.get('secret')
    if provided_secret != MY_SECRET:
        logger.warning(f"Invalid secret provided")
        return jsonify({"error": "Invalid secret"}), 403
    
    logger.info("Secret validation passed")
    
    task_id = data.get('task')
    round_num = data.get('round')
    
    try:
        # Extract data
        email = data.get('email')
        nonce = data.get('nonce')
        brief = data.get('brief')
        checks = data.get('checks', [])
        evaluation_url = data.get('evaluation_url')
        attachments = data.get('attachments', [])
        
        logger.info(f"\n=== STEP 1: GENERATE CODE ===")
        logger.info(f"Brief: {brief[:100]}...")
        logger.info(f"Checks: {len(checks)} criteria")
        
        # Step 1: Generate code using LLM
        try:
            generated_files = generate_app_code(brief, attachments, checks)
            logger.info(f"✓ Code generation completed. Files: {list(generated_files.keys())}")
        except Exception as e:
            logger.error(f"✗ CODE GENERATION FAILED: {str(e)}", exc_info=True)
            raise Exception(f"Code generation failed: {str(e)}")
        
        logger.info(f"\n=== STEP 2: CREATE GITHUB REPO ===")
        logger.info(f"Task ID: {task_id}")
        
        # Step 2: Create GitHub repo and deploy
        try:
            repo_url, commit_sha, pages_url = create_and_deploy_repo(
                task_id, 
                generated_files, 
                brief
            )
            logger.info(f"✓ Repository created: {repo_url}")
            logger.info(f"✓ Commit SHA: {commit_sha}")
            logger.info(f"✓ Pages URL: {pages_url}")
        except Exception as e:
            logger.error(f"✗ GITHUB DEPLOYMENT FAILED: {str(e)}", exc_info=True)
            raise Exception(f"GitHub deployment failed: {str(e)}")
        
        logger.info(f"\n=== STEP 3: NOTIFY EVALUATION SERVER ===")
        logger.info(f"Evaluation URL: {evaluation_url}")
        
        # Step 3: Notify the evaluation server
        try:
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
            logger.info("✓ Evaluation server notified")
        except Exception as e:
            logger.warning(f"⚠ Notification to evaluation server failed: {str(e)}")
            # Don't fail the entire request if notification fails
        
        logger.info("="*80)
        logger.info(f"✓ SUCCESSFULLY COMPLETED TASK {task_id}")
        logger.info("="*80)
        
        return jsonify({
            "status": "success",
            "message": f"Task {task_id} completed successfully",
            "repo_url": repo_url,
            "pages_url": pages_url,
            "commit_sha": commit_sha
        }), 200
        
    except Exception as e:
        logger.error("="*80)
        logger.error(f"✗ TASK FAILED: {str(e)}", exc_info=True)
        logger.error("="*80)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


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
                logger.info(f"✓ Notification successful on attempt {attempt + 1}")
                return True
            else:
                logger.warning(f"Attempt {attempt + 1} failed with status {response.status_code}")
        
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
        
        # Wait before retrying (exponential backoff)
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
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
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=not is_production,
        use_reloader=False,
        threaded=True
    )