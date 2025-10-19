import os
import subprocess
import tempfile
import shutil
import logging
from dotenv import load_dotenv
from github import Github
import time
import requests

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get credentials from .env
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')

logger.info(f"GitHub Manager initialized - Username: {GITHUB_USERNAME}")


def create_and_deploy_repo(task_id, generated_files, brief):
    """
    Creates a GitHub repository, pushes generated code, and enables GitHub Pages.
    
    Args:
        task_id (str): Unique task identifier (e.g., 'captcha-solver-abc123')
        generated_files (dict): Dictionary of {filename: content}
        brief (str): Task description
    
    Returns:
        tuple: (repo_url, commit_sha, pages_url)
    """
    
    logger.info(f"Starting repo creation for task: {task_id}")
    
    # Validate inputs
    if not GITHUB_TOKEN or not GITHUB_USERNAME:
        raise Exception("GitHub credentials not configured. Check GITHUB_TOKEN and GITHUB_USERNAME.")
    
    if not generated_files:
        raise Exception("No files provided to push to GitHub.")
    
    # Step 1: Create a temporary directory for the repo
    temp_dir = tempfile.mkdtemp()
    logger.info(f"Created temporary directory: {temp_dir}")
    
    try:
        # Step 2: Configure git in container
        logger.info("Configuring Git...")
        configure_git(GITHUB_USERNAME)
        
        # Step 3: Initialize Git repository locally
        logger.info("Initializing Git repository...")
        run_git_command(temp_dir, ['git', 'init'])
        run_git_command(temp_dir, ['git', 'config', 'user.name', GITHUB_USERNAME])
        run_git_command(temp_dir, ['git', 'config', 'user.email', f'{GITHUB_USERNAME}@example.com'])
        
        # Step 4: Create all files in the temporary directory
        logger.info("Writing files to repository...")
        for filename, content in generated_files.items():
            filepath = os.path.join(temp_dir, filename)
            # Create subdirectories if needed
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Created file: {filename} ({len(content)} bytes)")
        
        # Step 5: Create a .gitignore file
        gitignore_content = """__pycache__/
*.pyc
*.pyo
*.egg-info/
.DS_Store
.venv
venv/
node_modules/
"""
        with open(os.path.join(temp_dir, '.gitignore'), 'w') as f:
            f.write(gitignore_content)
        logger.info("Created .gitignore")
        
        # Step 6: Stage and commit files
        logger.info("Staging and committing files...")
        run_git_command(temp_dir, ['git', 'add', '.'])
        run_git_command(temp_dir, ['git', 'commit', '-m', f'Initial commit: {brief[:50]}'])
        
        # Step 7: Get the commit SHA
        commit_sha = get_commit_sha(temp_dir)
        logger.info(f"Commit SHA: {commit_sha}")
        
        # Step 8: Create repository on GitHub using PyGithub
        logger.info("Creating repository on GitHub...")
        repo_url, pages_url = create_github_repo(task_id, brief, temp_dir, GITHUB_TOKEN, GITHUB_USERNAME)
        
        logger.info(f"Repository created: {repo_url}")
        logger.info(f"GitHub Pages URL: {pages_url}")
        
        return repo_url, commit_sha, pages_url
    
    except Exception as e:
        logger.error(f"Repository creation failed: {str(e)}", exc_info=True)
        raise
    
    finally:
        # Cleanup: Remove temporary directory
        logger.info("Cleaning up temporary directory...")
        shutil.rmtree(temp_dir, ignore_errors=True)


def configure_git(username):
    """
    Configures git globally in the container.
    
    Args:
        username (str): GitHub username
    """
    try:
        subprocess.run(
            ['git', 'config', '--global', 'user.name', username],
            check=True,
            capture_output=True
        )
        subprocess.run(
            ['git', 'config', '--global', 'user.email', f'{username}@example.com'],
            check=True,
            capture_output=True
        )
        logger.info("Git configured globally")
    except Exception as e:
        logger.warning(f"Could not configure git globally: {str(e)}")


def run_git_command(working_dir, command):
    """
    Runs a git command in the specified directory.
    
    Args:
        working_dir (str): Directory to run command in
        command (list): Command and arguments
    
    Returns:
        str: Command output
    """
    
    try:
        logger.debug(f"Running git command: {' '.join(command)}")
        result = subprocess.run(
            command,
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        logger.debug(f"Command output: {result.stdout[:100]}")
        return result.stdout
    
    except subprocess.TimeoutExpired:
        logger.error(f"Git command timed out: {' '.join(command)}")
        raise Exception(f"Git command timed out: {' '.join(command)}")
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {' '.join(command)}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        raise Exception(f"Git command failed: {e.stderr}")
    
    except FileNotFoundError:
        logger.error("Git is not installed or not in PATH")
        raise Exception("Git is not installed. This is required for deployment.")


def get_commit_sha(repo_dir):
    """
    Gets the SHA of the last commit.
    """
    try:
        output = run_git_command(repo_dir, ['git', 'rev-parse', 'HEAD'])
        sha = output.strip()[:7]
        logger.info(f"Got commit SHA: {sha}")
        return sha
    except Exception as e:
        logger.error(f"Failed to get commit SHA: {str(e)}")
        raise


def create_github_repo(repo_name, description, local_repo_path, github_token, github_username):
    """
    Creates a GitHub repository and pushes local code to it.
    """
    
    try:
        logger.info("Authenticating with GitHub...")
        
        # Authenticate with GitHub
        g = Github(github_token)
        user = g.get_user()
        logger.info(f"Authenticated as: {user.login}")
        
        # Check if repo already exists
        logger.info(f"Checking if repository '{repo_name}' exists...")
        repo = None
        try:
            repo = user.get_repo(repo_name)
            logger.info(f"Repository '{repo_name}' already exists")
        except Exception as e:
            logger.info(f"Repository doesn't exist, creating new one...")
            # Create new repo
            repo = user.create_repo(
                name=repo_name,
                description=description,
                private=False,
                auto_init=False
            )
            logger.info(f"Repository created: {repo.html_url}")
        
        # Add remote and push
        logger.info("Configuring git remote and pushing code...")
        
        # Use token-based authentication
        remote_url = f"https://{github_token}@github.com/{github_username}/{repo_name}.git"
        
        try:
            run_git_command(local_repo_path, ['git', 'remote', 'add', 'origin', remote_url])
        except Exception as e:
            # Remote might already exist
            logger.warning(f"Could not add remote: {str(e)}, trying to update...")
            run_git_command(local_repo_path, ['git', 'remote', 'set-url', 'origin', remote_url])
        
        # Ensure main branch
        run_git_command(local_repo_path, ['git', 'branch', '-M', 'main'])
        
        # Push to GitHub
        logger.info("Pushing to GitHub...")
        run_git_command(local_repo_path, ['git', 'push', '-u', 'origin', 'main', '--force'])
        logger.info("Code pushed successfully!")
        
        # Enable GitHub Pages
        logger.info("Enabling GitHub Pages...")
        enable_github_pages(repo, github_token)
        
        # Construct URLs
        repo_url = repo.html_url
        pages_url = f"https://{github_username}.github.io/{repo_name}/"
        
        logger.info(f"Deployment complete!")
        logger.info(f"Repository: {repo_url}")
        logger.info(f"Pages URL: {pages_url}")
        
        return repo_url, pages_url
    
    except Exception as e:
        logger.error(f"Error creating GitHub repository: {str(e)}", exc_info=True)
        raise


def enable_github_pages(repo, github_token):
    """
    Enables GitHub Pages for the repository using GitHub REST API.
    """
    
    try:
        logger.info("Configuring GitHub Pages...")
        
        url = f"https://api.github.com/repos/{repo.owner.login}/{repo.name}/pages"
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        pages_config = {
            "source": {
                "branch": "main",
                "path": "/"
            }
        }
        
        logger.info(f"Sending GitHub Pages config to: {url}")
        
        # Try POST first (create Pages)
        response = requests.post(url, json=pages_config, headers=headers, timeout=10)
        
        logger.info(f"GitHub Pages POST response: {response.status_code}")
        
        # If already exists (409 Conflict), try PUT to update
        if response.status_code == 409:
            logger.info("Pages already exists, updating...")
            response = requests.put(url, json=pages_config, headers=headers, timeout=10)
            logger.info(f"GitHub Pages PUT response: {response.status_code}")
        
        if response.status_code in [200, 201, 204]:
            logger.info("GitHub Pages configured successfully")
            return True
        else:
            logger.warning(f"GitHub Pages configuration returned status {response.status_code}: {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Error configuring GitHub Pages: {str(e)}", exc_info=True)
        logger.warning("Pages may not be enabled, but repository was created")
        return False


def verify_github_pages(pages_url, max_retries=3):
    """
    Verifies that GitHub Pages is live and accessible.
    """
    
    logger.info(f"Verifying GitHub Pages at: {pages_url}")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(pages_url, timeout=10)
            if response.status_code == 200:
                logger.info("GitHub Pages is live!")
                return True
            else:
                logger.info(f"Attempt {attempt + 1}: Got status {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            logger.info(f"Attempt {attempt + 1}: {str(e)}")
        
        # Wait before retrying
        if attempt < max_retries - 1:
            wait_time = 5 * (attempt + 1)
            logger.info(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    logger.warning(f"GitHub Pages verification failed after {max_retries} attempts")
    return False