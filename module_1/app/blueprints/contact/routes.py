from flask import Blueprint, render_template

contact = Blueprint("contact", __name__)


@contact.route("/contact")
def contact_page():
    return render_template("contact.html", active="contact")
