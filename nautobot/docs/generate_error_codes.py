import os
from nautobot.core.utils.docs import generate_error_codes

app_name = "nautobot"
script_dir = os.path.dirname(os.path.abspath(__file__))  # docs/

generate_error_codes(app_name, script_dir)