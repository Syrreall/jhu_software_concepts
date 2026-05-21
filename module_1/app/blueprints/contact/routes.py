from flask import Blueprint, render_template

# Blueprint for the contact page
contact = Blueprint("contact", __name__)


@contact.route("/contact")
def contact_page():
    # active="contact" tells the navbar which tab to highlight
    return render_template("contact.html", active="contact")
