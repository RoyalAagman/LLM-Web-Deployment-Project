# LLM Code Deployment System

An automated system that generates web applications from task descriptions, creates GitHub repositories, and deploys them to GitHub Pages.

## Overview

This project automates the process of turning task specifications into live web applications. It integrates AI-powered code generation with GitHub automation to create a seamless deployment pipeline.

## Features

- **API-based Task Processing**: Accepts structured requests via HTTP POST
- **AI Code Generation**: Uses Google Gemini to generate HTML/CSS/JavaScript code
- **GitHub Automation**: Automatically creates repositories and manages version control
- **GitHub Pages Deployment**: Makes generated applications instantly accessible online
- **Security**: Secret-based authentication for request validation
- **Automatic Documentation**: Generates professional README and LICENSE files
- **Reliable Notifications**: Sends completion details with retry logic and exponential backoff
- **Error Handling**: Comprehensive error management and logging

## Technology Stack

- **Backend**: Python 3.8+, Flask
- **AI Model**: Google Gemini 2.5 Flash
- **Version Control**: Git, GitHub API (PyGithub)
- **Deployment**: GitHub Pages
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)

## Project Structure

```
llm_deployment_project/
├── app.py                  # Flask API endpoint
├── llm_generator.py        # Code generation engine
├── github_manager.py       # GitHub operations
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── README.md              # This file
└── venv/                  # Virtual environment (not committed)
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Git
- GitHub account
- Google Gemini API key

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/llm-deployment-project
   cd llm-deployment-project
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Create `.env` file in project root:
   ```env
   GITHUB_TOKEN=your_github_personal_access_token
   GEMINI_API_KEY=your_google_gemini_api_key
   YOUR_SECRET=your_custom_secret
   GITHUB_USERNAME=your_github_username
   ```

5. **Obtain API Keys**
   - **GitHub Token**: https://github.com/settings/tokens (requires `repo` and `workflow` scopes)
   - **Gemini API Key**: https://aistudio.google.com/apikey

6. **Run the server**
   ```bash
   python app.py
   ```
   API available at `http://localhost:5000/api-endpoint`

## Usage

### API Endpoint

**URL**: `http://localhost:5000/api-endpoint`
**Method**: POST
**Content-Type**: application/json

### Request Format

```json
{
  "email": "user@example.com",
  "secret": "your_custom_secret",
  "task": "unique-task-id",
  "round": 1,
  "nonce": "unique-nonce-string",
  "brief": "Description of what the web app should do",
  "checks": [
    "Evaluation criterion 1",
    "Evaluation criterion 2"
  ],
  "evaluation_url": "https://server.com/notify",
  "attachments": []
}
```

### Response

```json
{
  "status": "received",
  "message": "Processing task unique-task-id, round 1"
}
```

### Workflow

1. Request received and validated
2. Code generated using Gemini AI
3. GitHub repository created
4. Code pushed to repository
5. GitHub Pages configured
6. Completion notification sent to evaluation server

### Notification Payload

After processing, the system notifies the evaluation server with:

```json
{
  "email": "user@example.com",
  "task": "unique-task-id",
  "round": 1,
  "nonce": "unique-nonce-string",
  "repo_url": "https://github.com/username/unique-task-id",
  "commit_sha": "abc123def456",
  "pages_url": "https://username.github.io/unique-task-id/"
}
```

## Configuration

### Authentication

- **Request Secret**: Configured in `.env` as `YOUR_SECRET`
- **GitHub**: Uses personal access token for repository management
- **Gemini**: API key-based authentication

### Security Considerations

- `.env` file never committed (protected by `.gitignore`)
- GitHub token should have minimal required scopes
- Repositories created as public (per specification)
- No sensitive information stored in generated code

### GitHub Pages Setup

Repositories are configured with:
- Source: Deploy from branch `main`
- Path: Root directory `/`
- Automatic redeployment on push

## Testing

Create `test.ps1`:

```powershell
$headers = @{"Content-Type" = "application/json"}
$body = @{
    "email" = "test@example.com"
    "secret" = "your_custom_secret"
    "task" = "test-app-001"
    "round" = 1
    "nonce" = "test-nonce-001"
    "brief" = "Create a simple web application"
    "checks" = @("Application loads", "Works as expected")
    "evaluation_url" = "http://localhost:8000/eval"
    "attachments" = @()
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:5000/api-endpoint -Method POST -Headers $headers -Body $body
```

Run with: `.\test.ps1`

## System Components

**app.py**
- Receives and validates HTTP requests
- Manages request processing workflow
- Handles communication with other components
- Returns appropriate HTTP responses

**llm_generator.py**
- Interfaces with Gemini AI API
- Generates code from task specifications
- Processes attachments
- Creates documentation files

**github_manager.py**
- Manages Git operations
- Creates and configures repositories
- Handles GitHub API interactions
- Manages deployment configuration

## Performance

- Code generation: 30-60 seconds
- Repository creation: 5-10 seconds
- Code deployment: 10-15 seconds
- GitHub Pages availability: 1-2 minutes
- Total time start to live: 2-3 minutes

## Troubleshooting

**Invalid secret error**
- Verify `.env` contains correct `YOUR_SECRET`
- Ensure request uses matching secret value

**GitHub authentication failed**
- Verify GitHub token is valid
- Check token has required scopes
- Tokens may expire - create new one if needed

**API key error**
- Verify Gemini API key is correct
- Check account has available API quota
- Confirm API key has proper permissions

**GitHub Pages showing 404**
- Verify `index.html` exists in repository
- Check Pages settings in repository
- Ensure source branch is `main` and path is `/`
- Wait 1-2 minutes for deployment

**Git command failures**
- Verify Git is installed and accessible
- Check network connectivity
- Ensure repository URL is correct

## Environment Variables

```env
# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_USERNAME=your_github_username

# Google Gemini API
GEMINI_API_KEY=your_google_gemini_api_key

# Application Security
YOUR_SECRET=your_custom_secret_password
```

## Files Not Committed

The following are excluded from the repository (via `.gitignore`):
- `.env` (contains secrets)
- `venv/` (virtual environment)
- `__pycache__/` (Python cache)
- `*.pyc` (compiled Python)
- Test files

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review server logs for detailed error messages
3. Verify all environment variables are configured
4. Check GitHub repository status manually via GitHub.com