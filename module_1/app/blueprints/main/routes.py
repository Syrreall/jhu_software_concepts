from flask import Blueprint, render_template

# Blueprint for the homepage / about page
main = Blueprint("main", __name__)


@main.route("/")
def index():
    # active="about" tells the navbar which tab to highlight
    return render_template("index.html", active="about")
