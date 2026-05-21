from flask import Flask


def create_app():
    app = Flask(__name__)

    from app.blueprints.main.routes import main
    from app.blueprints.contact.routes import contact
    from app.blueprints.projects.routes import projects

    app.register_blueprint(main)
    app.register_blueprint(contact)
    app.register_blueprint(projects)

    return app
