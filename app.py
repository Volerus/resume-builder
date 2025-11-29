import json
import os
import sys
import shutil
from io import BytesIO
import uuid
from datetime import datetime

from flask import Flask, request, Response, render_template, jsonify
from openai import OpenAI
import yaml
from pdf_generator import generate_reduced_top_margin_resume

app = Flask(__name__)

# Constants
PROFILES_DIR = 'profiles'
DEFAULT_PROFILE = 'default'

# Global state
active_profile = DEFAULT_PROFILE

# Ensure profiles directory exists
if not os.path.exists(PROFILES_DIR):
    os.makedirs(PROFILES_DIR)

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
        'profile_history': os.path.join(storage_dir, 'profile_history.json')
    }

def migrate_to_profiles():
    """Migrate existing files to default profile if they exist in root."""
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

# Run migration on startup
migrate_to_profiles()

# Load secrets
with open("secrets.yaml", "r") as file:
    secrets = yaml.safe_load(file)

api_key = secrets["api_key"]
os.environ["API_KEY"] = api_key


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


def extract_company_name(job_description):
    """Extract company name from job description using OpenRouter API."""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("API_KEY")
    )
    
    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-001",
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


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


# Profile Management Endpoints

@app.route('/profiles', methods=['GET'])
def list_profiles():
    """List all available profiles."""
    profiles = [d for d in os.listdir(PROFILES_DIR) if os.path.isdir(os.path.join(PROFILES_DIR, d))]
    return jsonify({
        'profiles': profiles,
        'active': active_profile
    })

@app.route('/profiles', methods=['POST'])
def create_profile():
    """Create a new profile."""
    try:
        name = request.json.get('name')
        if not name:
            return jsonify({'error': 'Profile name is required'}), 400
            
        # Sanitize name (basic)
        name = "".join(x for x in name if x.isalnum() or x in ('-', '_'))
        
        target_dir = get_profile_dir(name)
        if os.path.exists(target_dir):
            return jsonify({'error': 'Profile already exists'}), 400
            
        os.makedirs(target_dir)
        
        # Initialize empty files
        with open(os.path.join(target_dir, 'resume_data.json'), 'w') as f:
            json.dump({}, f)
        with open(os.path.join(target_dir, 'info.json'), 'w') as f:
            json.dump({}, f)
            
        ensure_profile_dirs(name)
        
        return jsonify({'status': 'success', 'name': name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/profiles/switch', methods=['POST'])
def switch_profile():
    """Switch the active profile."""
    global active_profile
    try:
        name = request.json.get('name')
        if not name:
            return jsonify({'error': 'Profile name is required'}), 400
            
        target_dir = get_profile_dir(name)
        if not os.path.exists(target_dir):
            return jsonify({'error': 'Profile does not exist'}), 404
            
        active_profile = name
        return jsonify({'status': 'success', 'active': active_profile})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/profiles/<name>', methods=['DELETE'])
def delete_profile(name):
    """Delete a profile."""
    global active_profile
    try:
        if name == 'default':
            return jsonify({'error': 'Cannot delete default profile'}), 400
            
        if name == active_profile:
            return jsonify({'error': 'Cannot delete active profile'}), 400
            
        target_dir = get_profile_dir(name)
        if not os.path.exists(target_dir):
            return jsonify({'error': 'Profile does not exist'}), 404
            
        shutil.rmtree(target_dir)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/improve-resume', methods=['POST'])
def improve_resume():
    """Generate improved resume JSON and return comparison with original."""
    try:
        job_description = request.json['description']
        pre_prompt = request.json.get('pre_prompt')
        post_prompt = request.json.get('post_prompt')
        additional_context = request.json.get('additional_context')
        
        paths = get_profile_paths()
        
        # Load original resume
        if os.path.exists(paths['resume_data']):
            with open(paths['resume_data'], 'r') as file:
                original_resume = json.load(file)
        else:
            original_resume = {}
        
        # Prepare prompts
        if not pre_prompt:
            pre_prompt = ("Act as a JSON Data Processor and ATS Optimization Specialist\n"
                            "I am going to provide you with a **Resume in JSON format** and a **Target Job Description**.\n"
                            "Your task is to update the values inside the `work`, `professional_summary`, and `skills` arrays within the JSON to better match the Job Description.")
        
        if not post_prompt:
            post_prompt = ("**Strict Technical Constraints:**\n"
            "1.  **Output Format:** You must return **ONLY** valid, raw JSON. Do not include markdown formatting (like ```json), conversational filler, or explanations. Just the JSON object.\n"
            "2.  **Structure Integrity:** Do not change keys, variable names, or the overall structure of the JSON object.\n"
            "3.  **Minimal Edits:** You are allowed to change or insert a maximum of **3-4 specific keywords** to match the Job Description if necessary.\n"
            "4.  **Preserve Context:** Do not rewrite the sentences. Keep the original sentence structure and meaning, only swapping in technical terms or hard skills where they fit naturally.\n"
            "5. **Pick and Choose:** Based on the Job Description, pick and choose the most relevant 5 `highlights`  per `company`. When possible combine multiple highlights into just 5 highlights concising")
        
        # Call OpenRouter API to improve resume
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("API_KEY")
        )
        
        user_content = f"\nTarget Job Description\n{job_description}\n\nResume in JSON format\n{json.dumps(original_resume, indent=4)}\n\n{post_prompt}"
        
        if additional_context:
            user_content += f"\n\n**Additional Context/Instructions:**\n{additional_context}"
        
        messages = [
            {
                "role": "system",
                "content": pre_prompt
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
        
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash-lite-preview-09-2025",
            messages=messages
        )
        
        # Extract improved resume JSON
        improved_resume = extract_json_from_response(response.choices[0].message.content)
        
        # Extract company name
        company_name = extract_company_name(job_description)
        
        # Return both original and improved for comparison
        return jsonify({
            'original': original_resume,
            'improved': improved_resume,
            'company_name': company_name
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ai-edit-resume', methods=['POST'])
def ai_edit_resume():
    """Update resume data based on natural language instruction."""
    try:
        data = request.json
        instruction = data.get('instruction')
        current_data = data.get('current_data')
        
        if not instruction or not current_data:
            return jsonify({'error': 'Instruction and current data are required'}), 400
            
        # Prepare prompt
        system_prompt = "Act as a JSON Data Processor. Your task is to update the provided Resume JSON data based on the user's natural language instruction."
        
        user_prompt = f"""
Current Resume JSON:
{json.dumps(current_data, indent=2)}

Instruction:
{instruction}

**Strict Rules:**
1. Return ONLY the updated JSON object. No markdown, no explanations.
2. Maintain the exact same structure as the input JSON.
3. Only modify fields relevant to the instruction.
4. If the instruction implies adding a new item (like a job or skill), generate a reasonable structure for it matching existing items.
"""

        # Call OpenRouter API
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("API_KEY")
        )
        
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Extract and parse JSON
        updated_data = extract_json_from_response(response.choices[0].message.content)
        
        return jsonify(updated_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """Generate PDF from resume JSON data."""
    try:
        data = request.json
        resume_data = data['resume']
        company_name = data.get('company_name')
        if not company_name:
            company_name = 'default_company'
        
        paths = get_profile_paths()
        ensure_profile_dirs(active_profile)
        
        # Load personal info to merge with resume data
        if os.path.exists(paths['info']):
            with open(paths['info'], 'r') as file:
                info = json.load(file)
        else:
            info = {}
        
        # Merge resume data with personal info
        full_resume = {**resume_data, **info}
        
        # Create PDF in memory
        buffer = BytesIO()
        generate_reduced_top_margin_resume(buffer, full_resume)
        
        # Generate unique ID for this resume
        resume_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Create directory for this resume
        resume_dir = os.path.join(paths['storage'], resume_id)
        os.makedirs(resume_dir)
        
        # Save PDF
        pdf_path = os.path.join(resume_dir, "resume.pdf")
        with open(pdf_path, 'wb') as output_file:
            buffer.seek(0)
            output_file.write(buffer.read())
            
        # Save JSON
        json_path = os.path.join(resume_dir, "resume.json")
        with open(json_path, 'w') as f:
            json.dump(full_resume, f, indent=4)
            
        # Update history
        entry = {
            'id': resume_id,
            'company_name': company_name,
            'timestamp': timestamp,
            'pdf_path': pdf_path,
            'json_path': json_path
        }
        save_history_entry(entry)
        
        # Also save to company directory for backward compatibility/organization
        # Note: This still saves to root company dir, which might be desired or should be profile-scoped?
        # For now, let's keep it in root to avoid breaking existing workflow too much, 
        # or we could move it to profiles/<profile>/companies/<company>
        # Let's keep it simple and put it in the profile directory
        
        company_dir = os.path.join(paths['base'], company_name)
        if not os.path.exists(company_dir):
            os.makedirs(company_dir)
        
        company_pdf_path = os.path.join(company_dir, "resume.pdf")
        shutil.copy(pdf_path, company_pdf_path)
        
        # Return PDF as response
        buffer.seek(0)
        return Response(buffer, content_type='application/pdf')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/history', methods=['GET'])
def get_history():
    """Get list of generated resumes."""
    return jsonify(load_history())


@app.route('/download/<resume_id>/<file_type>', methods=['GET'])
def download_file(resume_id, file_type):
    """Download PDF or JSON for a specific resume."""
    try:
        history = load_history()
        entry = next((item for item in history if item['id'] == resume_id), None)
        
        if not entry:
            return jsonify({'error': 'Resume not found'}), 404
            
        if file_type == 'pdf':
            return Response(open(entry['pdf_path'], 'rb'), content_type='application/pdf')
        elif file_type == 'json':
            return jsonify(json.load(open(entry['json_path'], 'r')))
        else:
            return jsonify({'error': 'Invalid file type'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/profile', methods=['GET'])
def profile():
    return render_template('profile.html')


@app.route('/get-profile-data', methods=['GET'])
def get_profile_data():
    """Get current resume data merged with personal info."""
    try:
        paths = get_profile_paths()
        
        if os.path.exists(paths['resume_data']):
            with open(paths['resume_data'], 'r') as file:
                resume_data = json.load(file)
        else:
            resume_data = {}
            
        if os.path.exists(paths['info']):
            with open(paths['info'], 'r') as file:
                info_data = json.load(file)
        else:
            info_data = {}
            
        # Merge data
        data = {**resume_data, **info_data}
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/save-profile-data', methods=['POST'])
def save_profile_data():
    """Save new profile data (resume + info) and add to history."""
    try:
        new_data = request.json
        paths = get_profile_paths()
        ensure_profile_dirs(active_profile)
        
        # Load current data to save to history
        if os.path.exists(paths['resume_data']):
            with open(paths['resume_data'], 'r') as file:
                current_resume = json.load(file)
        else:
            current_resume = {}
            
        if os.path.exists(paths['info']):
            with open(paths['info'], 'r') as file:
                current_info = json.load(file)
        else:
            current_info = {}
            
        current_full_data = {**current_resume, **current_info}
            
        # Load existing history
        if os.path.exists(paths['profile_history']):
            with open(paths['profile_history'], 'r') as f:
                history = json.load(f)
        else:
            history = []
            
        # Add current version to history
        history_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'data': current_full_data
        }
        history.append(history_entry)
        
        # Save history
        with open(paths['profile_history'], 'w') as f:
            json.dump(history, f, indent=4)
            
        # Split and save new data
        resume_keys = ['work', 'skills', 'professional_summary']
        info_keys = ['basics', 'education']
        
        new_resume = {k: new_data.get(k) for k in resume_keys if k in new_data}
        new_info = {k: new_data.get(k) for k in info_keys if k in new_data}
        
        with open(paths['resume_data'], 'w') as f:
            json.dump(new_resume, f, indent=4)
            
        with open(paths['info'], 'w') as f:
            json.dump(new_info, f, indent=4)
            
        return jsonify({'status': 'success', 'history_id': history_entry['id']})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get-profile-history', methods=['GET'])
def get_profile_history():
    """Get profile version history."""
    try:
        paths = get_profile_paths()
        if os.path.exists(paths['profile_history']):
            with open(paths['profile_history'], 'r') as f:
                history = json.load(f)
            return jsonify(history)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/restore-profile-version', methods=['POST'])
def restore_profile_version():
    """Restore a specific version from history."""
    try:
        version_id = request.json['id']
        paths = get_profile_paths()
        
        with open(paths['profile_history'], 'r') as f:
            history = json.load(f)
            
        version = next((item for item in history if item['id'] == version_id), None)
        
        if not version:
            return jsonify({'error': 'Version not found'}), 404
            
        data = version['data']
        
        resume_keys = ['work', 'skills', 'professional_summary']
        info_keys = ['basics', 'education']
        
        new_resume = {k: data.get(k) for k in resume_keys if k in data}
        new_info = {k: data.get(k) for k in info_keys if k in data}
        
        with open(paths['resume_data'], 'w') as f:
            json.dump(new_resume, f, indent=4)
            
        if new_info:
            with open(paths['info'], 'w') as f:
                json.dump(new_info, f, indent=4)
            
        return jsonify({'status': 'success'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    return {
        'status': 'healthy'
    }


if __name__ == '__main__':
    app.run()
