import os
from dotenv import load_dotenv
import base64
import json
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)


def generate_app_code(brief, attachments, checks):
    """
    Uses Google Gemini to generate a complete web application based on the brief.
    
    Args:
        brief (str): Description of what the app should do
        attachments (list): List of files (with data URIs)
        checks (list): List of criteria the app must meet
    
    Returns:
        dict: Dictionary with filenames as keys and file contents as values
        Example: {
            'index.html': '<html>...</html>',
            'README.md': '# Project...',
            'LICENSE': 'MIT License...'
        }
    """
    
    print("🤖 Asking Google Gemini to generate code...")
    
    # Step 1: Process attachments and convert data URIs to actual content
    processed_attachments = process_attachments(attachments)
    
    # Step 2: Create a detailed prompt for the LLM
    prompt = create_prompt(brief, processed_attachments, checks)
    
    # Step 3: Call Gemini API
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Step 4: Extract the generated code
        generated_code = response.text
        
        print("✅ Code generated successfully!")
        
        # Step 5: Parse the response and create files
        files = parse_generated_code(generated_code, processed_attachments)
        
        # Step 6: Add mandatory files (LICENSE and README)
        files['LICENSE'] = generate_mit_license()
        files['README.md'] = generate_readme(brief, checks)
        
        return files
    
    except Exception as e:
        print(f"❌ Error generating code: {str(e)}")
        raise


def process_attachments(attachments):
    """
    Converts data URI attachments to usable content.
    
    Args:
        attachments: List of dicts with 'name' and 'url' (data URI)
    
    Returns:
        dict: {filename: content}
    """
    processed = {}
    
    for attachment in attachments:
        name = attachment.get('name')
        data_uri = attachment.get('url')
        
        if not data_uri or not data_uri.startswith('data:'):
            continue
        
        try:
            # Parse data URI: data:type;base64,content
            header, encoded = data_uri.split(',', 1)
            
            # Decode base64 content
            if 'base64' in header:
                content = base64.b64decode(encoded).decode('utf-8')
            else:
                content = encoded
            
            processed[name] = content
            print(f"📎 Processed attachment: {name}")
        
        except Exception as e:
            print(f"⚠️ Failed to process attachment {name}: {str(e)}")
    
    return processed


def create_prompt(brief, attachments, checks):
    """
    Creates a detailed prompt for Gemini.
    """
    
    prompt = f"""Create a complete single-page web application with these requirements:

**Task Description:**
{brief}

**Evaluation Criteria:**
"""
    
    for i, check in enumerate(checks, 1):
        prompt += f"{i}. {check}\n"
    
    if attachments:
        prompt += f"\n**Attached Files:**\n"
        for filename, content in attachments.items():
            prompt += f"\nFile: {filename}\n```\n{content[:500]}...\n```\n"
    
    prompt += """

**Requirements:**
1. Create a SINGLE index.html file that includes all HTML, CSS (in <style> tags), and JavaScript (in <script> tags)
2. The page must work when deployed to GitHub Pages (no server-side code, pure static HTML/CSS/JS)
3. Use CDN links for any external libraries (Bootstrap, jQuery, etc.)
4. Make sure all the evaluation criteria are met
5. The code should be clean, well-commented, and functional
6. Include error handling for edge cases

IMPORTANT: Start your response with the code directly. Begin with <html> tag and end with </html> tag.
Do NOT include markdown formatting like ```html or ```. Just the raw HTML code.
"""
    
    return prompt


def parse_generated_code(generated_code, attachments):
    """
    Extracts code from Gemini response and creates file structure.
    
    Args:
        generated_code (str): The Gemini response
        attachments (dict): Processed attachments to include
    
    Returns:
        dict: {filename: content}
    """
    
    files = {}
    
    # Remove markdown code blocks if present
    code = generated_code.strip()
    
    # Check if response contains ```html markers
    if '```html' in code:
        # Extract content between ```html and ```
        start = code.find('```html') + 7
        end = code.find('```', start)
        code = code[start:end].strip()
    elif '```' in code:
        # Extract content between ``` and ```
        start = code.find('```') + 3
        end = code.find('```', start)
        code = code[start:end].strip()
    
    # Find the actual HTML content
    if '<html' in code.lower():
        # Extract from <html to </html>
        start = code.lower().find('<html')
        end = code.lower().find('</html>') + 7
        if start != -1 and end > start:
            code = code[start:end]
    
    # Save as index.html
    files['index.html'] = code
    
    # Include attachments as separate files
    for filename, content in attachments.items():
        files[filename] = content
    
    return files


def generate_mit_license():
    """
    Generates an MIT License text.
    """
    
    from datetime import datetime
    year = datetime.now().year
    
    license_text = f"""MIT License

Copyright (c) {year}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    
    return license_text


def generate_readme(brief, checks):
    """
    Generates a professional README.md file.
    
    Args:
        brief (str): Task description
        checks (list): Evaluation criteria
    
    Returns:
        str: README content in markdown
    """
    
    readme = f"""# Web Application

## Overview
{brief}

## Features
This application implements the following features:
"""
    
    for i, check in enumerate(checks, 1):
        readme += f"{i}. {check}\n"
    
    readme += """

## Setup
1. Clone this repository
2. Open `index.html` in a web browser
3. Or visit the GitHub Pages deployment

## Usage
The application runs entirely in the browser. Simply open the page and follow the on-screen instructions.

## Technology Stack
- HTML5
- CSS3
- JavaScript (ES6+)
- External libraries loaded via CDN

## Code Structure
- `index.html` - Main application file containing all HTML, CSS, and JavaScript
- `LICENSE` - MIT License
- `README.md` - This file

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Deployment
This application is deployed using GitHub Pages and is accessible at the repository's GitHub Pages URL.
"""
    
    return readme