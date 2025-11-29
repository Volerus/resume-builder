# Resume Builder

A Flask-based Resume Builder application that helps you create, manage, and improve your resume using AI.

## Features

-   **Profile Management**: Create and manage multiple resume profiles.
-   **AI Resume Improvement**: Use AI to tailor your resume for specific job descriptions.
-   **PDF Generation**: Generate professional PDFs of your resume.
-   **Version History**: Track changes and revert to previous versions of your resume.
-   **Customizable Prompts**: Fine-tune the AI's behavior with custom prompts.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd resume-builder
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Secrets**:
    Create a `secrets.yaml` file in the root directory with your API key:
    ```yaml
    api_key: "your_api_key_here"
    ```

## Running the Application

Run the application using the `run.py` script:

```bash
python run.py
```

The application will be available at `http://127.0.0.1:5001`.

## Project Structure

-   `app/`: Contains the application logic.
    -   `__init__.py`: Flask app factory.
    -   `routes.py`: API endpoints and routes.
    -   `services.py`: Business logic and helper functions.
    -   `pdf_generator.py`: PDF generation logic.
    -   `templates/`: HTML templates.
    -   `static/`: Static assets (CSS, JS).
-   `profiles/`: Stores user profiles and generated resumes.
-   `run.py`: Entry point for the application.
-   `secrets.yaml`: Configuration file for secrets (not committed).

## Usage

1.  **Home Page**: The main interface for editing your resume and generating PDFs.
2.  **Profiles**: Manage different versions of your resume for different purposes.
3.  **Improve Resume**: Paste a job description to get AI-suggested improvements.
