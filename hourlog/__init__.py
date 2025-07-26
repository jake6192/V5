# Init for hourlog
from flask import Blueprint
bp = Blueprint('hourlog', __name__)

from hourlog import routes
