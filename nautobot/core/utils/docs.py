

import os
from jinja2 import Environment, FileSystemLoader
from nautobot.extras.registry import registry

import mkdocs_gen_files

def generate_error_codes(app_name, script_dir):

    base_dir = os.path.join(os.path.dirname(script_dir), app_name)

    for dir_name in os.listdir(base_dir):
        app_dir = os.path.join(base_dir, dir_name)
        if os.path.isdir(app_dir):
            error_codes_path = os.path.join(app_dir, "error_codes.py")
            if os.path.isfile(error_codes_path):
                try:
                    # Dynamically import the error_codes module
                    module_name = f"{app_name}.{dir_name}.error_codes"
                    __import__(module_name, fromlist=["*"])
                    print(module_name)
                except ModuleNotFoundError:
                    # Skip if the error_codes.py module cannot be imported
                    continue

    template_dir = script_dir  # Templates live in docs/
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

    virtual_path = os.path.join("user-guide", "administration", "troubleshooting")

    os.makedirs(virtual_path, exist_ok=True)

    template = env.get_template("error_code_template.j2")

    for error_code, error in registry["error_codes"].items():
        data = {
            "error_code": error_code,
            "error": error,
        }
        doc_path = f"{error_code}.md"
        
        output_content = template.render(**data)
        doc_path = os.path.join(virtual_path, f"{error_code}.md")
        output_content = template.render(**data)

        # Use mkdocs_gen_files to write the virtual file
        with mkdocs_gen_files.open(doc_path, "w") as fd:
            fd.write(output_content)

