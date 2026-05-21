from flask import Blueprint, render_template

# Blueprint for the projects / publications page
projects = Blueprint("projects", __name__)


@projects.route("/projects")
def projects_page():
    # active="projects" tells the navbar which tab to highlight
    return render_template("projects.html", active="projects")
