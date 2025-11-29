from flask import Flask
import os
import yaml

def create_app():
    app = Flask(__name__)

    # Load secrets
    # Note: secrets.yaml is expected to be in the root directory
    secrets_path = os.path.join(os.getcwd(), "secrets.yaml")
    if os.path.exists(secrets_path):
        with open(secrets_path, "r") as file:
            secrets = yaml.safe_load(file)
            app.config["API_KEY"] = secrets.get("api_key")
            os.environ["API_KEY"] = secrets.get("api_key") # Set env var for services that might use it directly

    from .routes import main
    app.register_blueprint(main)

    from .services import migrate_to_profiles
    migrate_to_profiles()

    return app
