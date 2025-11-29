import os
import json
import shutil
from openai import OpenAI
from datetime import datetime

# Constants
PROFILES_DIR = 'profiles'
DEFAULT_PROFILE = 'default'

# Global state (simulated for now, ideally should be session based or database)
active_profile = DEFAULT_PROFILE

def get_active_profile():
    return active_profile

def set_active_profile(name):
    global active_profile
    active_profile = name

def get_profile_dir(profile_name):
    return os.path.join(PROFILES_DIR, profile_name)

def get_profile_paths(profile_name=None):
    if profile_name is None:
        profile_name = active_profile
    
    base_dir = get_profile_dir(profile_name)
    storage_dir = os.path.join(base_dir, 'generated')
    
    return {
        'base': base_dir,
        'resume_data': os.path.join(base_dir, 'resume_data.json'),
        'info': os.path.join(base_dir, 'info.json'),
        'storage': storage_dir,
        'history': os.path.join(storage_dir, 'history.json'),
        'profile_history': os.path.join(storage_dir, 'profile_history.json'),
        'prompts': os.path.join(base_dir, 'prompts.json')
    }

def ensure_profile_dirs(profile_name):
    paths = get_profile_paths(profile_name)
    if not os.path.exists(paths['storage']):
        os.makedirs(paths['storage'])
    
    if not os.path.exists(paths['history']):
        with open(paths['history'], 'w') as f:
            json.dump([], f)
            
    if not os.path.exists(paths['profile_history']):
        with open(paths['profile_history'], 'w') as f:
            json.dump([], f)

def load_history():
    paths = get_profile_paths()
    ensure_profile_dirs(active_profile)
    if os.path.exists(paths['history']):
        with open(paths['history'], 'r') as f:
            return json.load(f)
    return []

def save_history_entry(entry):
    paths = get_profile_paths()
    ensure_profile_dirs(active_profile)
    history = load_history()
    history.append(entry)
    with open(paths['history'], 'w') as f:
        json.dump(history, f, indent=4)

def extract_json_from_response(content):
    """Extract JSON from AI response, handling markdown code blocks."""
    content = content.strip()
    
    # Check if content is wrapped in markdown code blocks
    if content.startswith('```'):
        # Remove opening ```json or ```
        lines = content.split('\n')
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        content = '\n'.join(lines)
    
    return json.loads(content)

def extract_company_name(job_description, model='google/gemini-2.0-flash-001'):
    """Extract company name from job description using OpenRouter API."""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("API_KEY")
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": f"\nJob Description\n{job_description}\nJust give me name of the company and nothing "
                          "else based of job description. Nothing else. If "
                          "the company has two words append using _ "
            }
        ]
    )
    
    return response.choices[0].message.content.strip()

def migrate_to_profiles():
    """Migrate existing files to default profile if they exist in root."""
    if not os.path.exists(PROFILES_DIR):
        os.makedirs(PROFILES_DIR)

    default_dir = get_profile_dir(DEFAULT_PROFILE)
    
    # If default profile doesn't exist, create it
    if not os.path.exists(default_dir):
        os.makedirs(default_dir)
        
        # Files to migrate
        files_to_move = [
            ('resume_data.json', 'resume_data.json'),
            ('info.json', 'info.json'),
        ]
        
        # Move files
        for src, dst in files_to_move:
            if os.path.exists(src):
                shutil.move(src, os.path.join(default_dir, dst))
            elif dst == 'resume_data.json':
                # Create empty resume data if it doesn't exist
                with open(os.path.join(default_dir, dst), 'w') as f:
                    json.dump({}, f)
        
        # Move generated directory
        if os.path.exists('generated'):
            if os.path.exists(os.path.join(default_dir, 'generated')):
                shutil.rmtree(os.path.join(default_dir, 'generated'))
            shutil.move('generated', os.path.join(default_dir, 'generated'))
        else:
            os.makedirs(os.path.join(default_dir, 'generated'))
