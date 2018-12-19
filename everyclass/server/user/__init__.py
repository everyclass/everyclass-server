from flask import Blueprint

user_bp = Blueprint('user', __name__)

from everyclass.server.user.views import login
