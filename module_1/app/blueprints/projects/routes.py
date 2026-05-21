from flask import Blueprint, render_template

projects = Blueprint("projects", __name__)


@projects.route("/projects")
def projects_page():
    return render_template("projects.html", active="projects")
