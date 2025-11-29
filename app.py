import json
import os
import sys

from flask import Flask, request, Response, render_template
from flask import jsonify
import requests
from openai import OpenAI
import yaml
from pdf_generator import generate_reduced_top_margin_resume
from io import BytesIO

app = Flask(__name__)

# Determine resume data file based on command-line argument
if len(sys.argv) > 1:
    resume_name = sys.argv[1]
    RESUME_DATA_FILE = f'resume_data_{resume_name}.json'
else:
    RESUME_DATA_FILE = 'resume_data.json'

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


@app.route('/improve-resume', methods=['POST'])
def improve_resume():
    """Generate improved resume JSON and return comparison with original."""
    try:
        job_description = request.json['description']
        
        # Load original resume
        with open(RESUME_DATA_FILE, 'r') as file:
            original_resume = json.load(file)
        
        # Prepare prompts
        pre_prompt = ("Act as a JSON Data Processor and ATS Optimization Specialist",
                        "I am going to provide you with a **Resume in JSON format** and a **Target Job Description**.",
                        "Your task is to update the values inside the `work`, `professional_summary`, and `skills` arrays within the JSON to better match the Job Description.")
        
        post_prompt = ("**Strict Technical Constraints:**",
        "1.  **Output Format:** You must return **ONLY** valid, raw JSON. Do not include markdown formatting (like ```json), conversational filler, or explanations. Just the JSON object.",
        "2.  **Structure Integrity:** Do not change keys, variable names, or the overall structure of the JSON object.",
        "3.  **Minimal Edits:** You are allowed to change or insert a maximum of **3-4 specific keywords** to match the Job Description if necessary."
        "4.  **Preserve Context:** Do not rewrite the sentences. Keep the original sentence structure and meaning, only swapping in technical terms or hard skills where they fit naturally.",
        "5. **Pick and Choose:** Based on the Job Description, pick and choose the most relevant 5 `highlights`  per `company`. When possible combine multiple highlights into just 5 highlights concising")
        
        # Call OpenRouter API to improve resume
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("API_KEY")
        )
        
        messages = [
            {
                "role": "system",
                "content": "Act as a JSON Data Processor and ATS Optimization Specialist."
            },
            {
                "role": "user",
                "content": f"\nTarget Job Description\n{job_description}\n\nResume in JSON format\n{json.dumps(original_resume, indent=4)}\n\n{post_prompt}"
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


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """Generate PDF from resume JSON data."""
    try:
        data = request.json
        resume_data = data['resume']
        company_name = data.get('company_name')
        if not company_name:
            company_name = 'default_company'
        
        # Load personal info to merge with resume data
        with open('info.json', 'r') as file:
            info = json.load(file)
        
        # Merge resume data with personal info
        full_resume = {**resume_data, **info}
        
        # Create PDF in memory
        buffer = BytesIO()
        generate_reduced_top_margin_resume(buffer, full_resume)
        
        # Create company directory if it doesn't exist
        if not os.path.exists(company_name):
            os.makedirs(company_name)
        
        # Save PDF to company directory
        full_path = os.path.join(company_name, "resume.pdf")
        with open(full_path, 'wb') as output_file:
            buffer.seek(0)
            output_file.write(buffer.read())
        
        # Return PDF as response
        buffer.seek(0)
        return Response(buffer, content_type='application/pdf')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@app.route('/make', methods=['POST'])
def gpt3_response():
    # Get the input text from the request

    buffer = BytesIO()

    pre_prompt = ("Act as a JSON Data Processor and ATS Optimization Specialist",
                        "I am going to provide you with a **Resume in JSON format** and a **Target Job Description**.",
                        "Your task is to update the values inside the `work`, `professional_summary`, and `skills` arrays within the JSON to better match the Job Description.")
    job_description = request.json['description']
    with open(RESUME_DATA_FILE, 'r') as file:
        resume_data = json.load(file)

    resume = json.dumps(resume_data, indent=4)

    post_prompt = ("**Strict Technical Constraints:**",
        "1.  **Output Format:** You must return **ONLY** valid, raw JSON. Do not include markdown formatting (like ```json), conversational filler, or explanations. Just the JSON object.",
        "2.  **Structure Integrity:** Do not change keys, variable names, or the overall structure of the JSON object.",
        "3.  **Minimal Edits:** You are allowed to change or insert a maximum of **3-4 specific keywords** to match the Job Description if necessary."
        "4.  **Preserve Context:** Do not rewrite the sentences. Keep the original sentence structure and meaning, only swapping in technical terms or hard skills where they fit naturally.",
        "5. **Pick and Choose:** Based on the Job Description, pick and choose the most relevant 5 `highlights`  per `company`. When possible combine multiple highlights into just 5 highlights concising")

    # print(input_text)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("API_KEY")
    )

    messages = [
        {
            "role": "system",
            "content": "You are a resume writer.You improve the resume which will increase "
                       "the chances for it to be picked for a given job description. "
        },
        {
            "role": "user",
            "content": "\nJob Description\n" + job_description + "\nResume Json\n" + str(resume) + "\n" + post_prompt
        }
    ]

    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=messages
    )

    # print(response['choices'][0]['message']['content'])
    data = extract_json_from_response(response.choices[0].message.content)

    with open('info.json', 'r') as file:
        info = json.load(file)

    full_resume = {**data, **info}

    print(json.dumps(full_resume, indent=4))

    generate_reduced_top_margin_resume(buffer, full_resume)

    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[
            {
                "role": "user",
                "content": "\nJob Description\n" + job_description + "Just give me name of the company and nothing "
                                                                     "else based of job description.Nothing else. If "
                                                                     "the company has two words append using _ "
            }]
    )

    company_name = response.choices[0].message.content

    print("----------------")
    print(company_name)
    print("----------------")

    if not os.path.exists(company_name):
        os.makedirs(company_name)

    # Full path to the output file
    full_path = os.path.join(company_name, "resume.pdf")

    # Write the buffer contents to the file
    with open(full_path, 'wb') as output_file:
        buffer.seek(0)
        output_file.write(buffer.read())

    buffer.seek(0)

    return Response(buffer, content_type='application/pdf')

    # return {
    #     'response_text': response.to_dict()["choices"][0]["text"]
    # }


@app.route('/health', methods=['GET'])
def health_check():
    return {
        'status': 'healthy'
    }


if __name__ == '__main__':
    app.run()
