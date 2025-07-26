# Init for member_tracking
from flask import Blueprint
bp = Blueprint('member_tracking', __name__)

from . import routes  # or other route modules
