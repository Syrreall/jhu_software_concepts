from flask import Flask


def create_app():
    # Application factory — creates and configures the Flask app
    app = Flask(__name__)

    # Import and register each page blueprint
    from app.blueprints.main.routes import main
    from app.blueprints.contact.routes import contact
    from app.blueprints.projects.routes import projects

    app.register_blueprint(main)
    app.register_blueprint(contact)
    app.register_blueprint(projects)

    return app
