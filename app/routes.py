from flask import Blueprint, request, Response, render_template, jsonify
from openai import OpenAI
import os
import json
import uuid
from io import BytesIO
from datetime import datetime
import shutil

from .services import (
    get_profile_paths, ensure_profile_dirs, load_history, save_history_entry,
    extract_json_from_response, extract_company_name,
    get_active_profile, set_active_profile, get_profile_dir, PROFILES_DIR, DEFAULT_PROFILE
)
from .pdf_generator import generate_reduced_top_margin_resume

main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def index():
    return render_template('index.html')


# Profile Management Endpoints

@main.route('/profiles', methods=['GET'])
def list_profiles():
    """List all available profiles."""
    if not os.path.exists(PROFILES_DIR):
        os.makedirs(PROFILES_DIR)
    profiles = [d for d in os.listdir(PROFILES_DIR) if os.path.isdir(os.path.join(PROFILES_DIR, d))]
    return jsonify({
        'profiles': profiles,
        'active': get_active_profile()
    })

@main.route('/profiles', methods=['POST'])
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

@main.route('/profiles/switch', methods=['POST'])
def switch_profile():
    """Switch the active profile."""
    try:
        name = request.json.get('name')
        if not name:
            return jsonify({'error': 'Profile name is required'}), 400
            
        target_dir = get_profile_dir(name)
        if not os.path.exists(target_dir):
            return jsonify({'error': 'Profile does not exist'}), 404
            
        set_active_profile(name)
        return jsonify({'status': 'success', 'active': name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/profiles/<name>', methods=['DELETE'])
def delete_profile(name):
    """Delete a profile."""
    try:
        if name == 'default':
            return jsonify({'error': 'Cannot delete default profile'}), 400
            
        if name == get_active_profile():
            return jsonify({'error': 'Cannot delete active profile'}), 400
            
        target_dir = get_profile_dir(name)
        if not os.path.exists(target_dir):
            return jsonify({'error': 'Profile does not exist'}), 404
            
        shutil.rmtree(target_dir)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/improve-resume', methods=['POST'])
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
            "4.  **Preserve Context:** Do not rewrite the sentences. Keep the original sentence structure and meaning, only swapping in technical terms or hard skills where they fit naturally.\n")
        
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


@main.route('/ai-edit-resume', methods=['POST'])
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


@main.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """Generate PDF from resume JSON data."""
    try:
        data = request.json
        resume_data = data['resume']
        company_name = data.get('company_name')
        if not company_name:
            company_name = 'default_company'
        
        paths = get_profile_paths()
        ensure_profile_dirs(get_active_profile())
        
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


@main.route('/history', methods=['GET'])
def get_history():
    """Get list of generated resumes."""
    return jsonify(load_history())


@main.route('/download/<resume_id>/<file_type>', methods=['GET'])
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


@main.route('/profile', methods=['GET'])
def profile():
    return render_template('profile.html')


@main.route('/get-profile-data', methods=['GET'])
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


@main.route('/save-profile-data', methods=['POST'])
def save_profile_data():
    """Save new profile data (resume + info) and add to history."""
    try:
        new_data = request.json
        paths = get_profile_paths()
        ensure_profile_dirs(get_active_profile())
        
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


@main.route('/get-profile-history', methods=['GET'])
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


@main.route('/restore-profile-version', methods=['POST'])
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


@main.route('/get-prompts', methods=['GET'])
def get_prompts():
    """Get saved prompts for the active profile."""
    try:
        paths = get_profile_paths()
        if os.path.exists(paths['prompts']):
            with open(paths['prompts'], 'r') as f:
                return jsonify(json.load(f))
        return jsonify({})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/save-prompts', methods=['POST'])
def save_prompts():
    """Save prompts for the active profile."""
    try:
        data = request.json
        paths = get_profile_paths()
        ensure_profile_dirs(get_active_profile())
        
        with open(paths['prompts'], 'w') as f:
            json.dump(data, f, indent=4)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/health', methods=['GET'])
def health_check():
    return {
        'status': 'healthy'
    }
