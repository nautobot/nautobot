# refactor imports
# find nautobot/appname/ -iname "*.py" -exec python refactor_imports.py {} \;
import argparse
import functools
import os
import re

from isort import place_module

import nautobot


class TopLevelImport:
    @classmethod
    def strip(cls):
        return cls


@functools.total_ordering
class ImportedName:
    def __init__(self, package_name, name):
        self.package_name = package_name
        if isinstance(name, str) and " as " in name:
            self._name = name.split(" as ")[0]
            self.alias = name.split(" as ")[1]
        else:
            self._name = name
            self.alias = None

    @property
    def name(self):
        if self.alias:
            return self.alias
        return self._name

    @property
    def name_str(self):
        if self.alias:
            return f"{self._name} as {self.alias}"
        return self._name

    def set_alias(self, alias):
        self.alias = alias

    def set_name(self, name):
        self._name = name

    def __str__(self):
        if self.name == TopLevelImport:
            return f"import {self.package_name}"
        return f"from {self.package_name} import {self.name}"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return all((self.package_name == other.package_name, self.name == other.name))

    def __hash__(self):
        return hash((self.package_name, self._name, self.alias))

    def __lt__(self, other):
        if self.package_name != other.package_name:
            return self.package_name.lower() < other.package_name.lower()
        if self.name == TopLevelImport:
            return True
        if other.name == TopLevelImport:
            return False
        return self.name.lower() < other.name.lower()


class NautobotImports:

    regexImport = re.compile(r"^import\s+(.*)\s*$")
    regexFromImport = re.compile(r"^from\s+(\S+)\s+import\s+(.*)\s*$")
    nautobot_base = os.path.dirname(nautobot.__file__)
    imports = {"stdlib": [], "nautobot": [], "other": []}
    replacements = []
    output_content = ""
    first_import_line_nbr = None

    def __init__(self, filename, data):
        self.filename = filename
        self.data = data
        self.dirname = os.path.dirname(filename)
        self.basename = os.path.basename(filename)
        self.python_library_path = self.dirname.replace("/", ".")
        self.enumerate_imports()
        self.fix_imports()
        self.insert_new_imports()
        self.replace_content()

    def add_import(self, package_name, name=TopLevelImport):
        package_name = package_name.strip()
        name = name.strip()
        if name == "" or package_name == "":
            return
        category = self.categorize_import(package_name)
        imported_obj = ImportedName(package_name, name)
        if imported_obj not in self.imports[category]:
            self.imports[category].append(imported_obj)

    def categorize_import(self, package_name):
        if package_name.startswith("nautobot") or package_name.startswith("."):
            return "nautobot"
        elif place_module(package_name) == "STDLIB":
            return "stdlib"
        else:
            return "other"

    def build_imports(self):
        output = ""
        for category in ["stdlib", "other", "nautobot"]:
            cur_line = []
            for imported_name in sorted(self.imports[category]):
                if cur_line and imported_name.package_name != cur_line[0].package_name:
                    names = ", ".join([n.name_str for n in cur_line])
                    output += f"from {cur_line[0].package_name} import {names}\n"
                    cur_line = []
                if imported_name.name == TopLevelImport:
                    output += f"import {imported_name.package_name}\n"
                else:
                    cur_line.append(imported_name)
            if cur_line:
                names = ", ".join([n.name_str for n in cur_line])
                output += f"from {cur_line[0].package_name} import {names}\n"
            if self.imports[category]:
                output += "\n"
        return output

    def enumerate_imports(self):
        imports = {}
        multi_line = ""
        self.first_import_line_nbr = 9999

        for line_nbr, line in enumerate(self.data.split("\n")):

            # handle multi-line imports
            if multi_line:
                if re.match(r"^\s*\)?\s*$", line):
                    multi_line = ""
                    continue
                imports.setdefault(multi_line, [])
                for name in line.strip().split(","):
                    # imports[multi_line].append(name.strip())
                    self.add_import(multi_line, name)

            # handle module imports (import os, re)
            match = self.regexImport.match(line)
            if match:
                if match.group(1) == "(":
                    raise Exception(f"unexpected multi-line import: {line}")
                for name in match.group(1).strip().split(","):
                    # imports[name].append(TopLevelImport)
                    self.add_import(name)

            # handle name imports (from xyz import Abc, 123)
            match = self.regexFromImport.match(line)
            if match:
                # wildcard imports only allowed in __init__.py
                if match.group(2).strip() == "*" and self.basename != "__init__.py":
                    raise Exception(f"unsupported wildcard import in {self.filename}")

                package = match.group(1)
                if match.group(2) == "(":
                    multi_line = match.group(1)
                    continue
                for name in match.group(2).strip().split(","):
                    self.add_import(package, name)

            if not any([multi_line, self.regexImport.match(line), self.regexFromImport.match(line)]):
                self.output_content += f"{line}\n"
            else:
                self.first_import_line_nbr = min(line_nbr, self.first_import_line_nbr)

    def fix_imports(self):
        for imported_name in self.imports["nautobot"]:
            if imported_name.package_name == ".":
                imported_name.package_name = self.python_library_path
                continue
            elif imported_name.package_name.startswith("."):
                imported_name.package_name = self.python_library_path + "." + imported_name.package_name[1:]

            # don't try to fix wildcard imports
            if imported_name.name == "*":
                continue

            if imported_name.name != TopLevelImport and imported_name.package_name.startswith("nautobot"):
                package_path = imported_name.package_name[9:].replace(".", "/")
                path = f"{self.nautobot_base}/{package_path}/{imported_name.name}"
                if not (os.path.exists(f"{path}.py") or os.path.exists(f"{path}/__init__.py")):
                    old_name = imported_name.name
                    containing_module = ".".join(imported_name.package_name.split(".")[:-1])
                    name = imported_name.package_name.split(".")[-1]
                    imported_name.package_name = containing_module
                    imported_name.set_name(name)
                    # keep track of these ones for regex replacement later
                    self.replacements.append((re.compile(re.escape(old_name)), f"{name}.{old_name}"))

        # deduplicate imports
        deduplicated = sorted(list(set(self.imports["nautobot"])))
        self.imports["nautobot"] = deduplicated

    def insert_new_imports(self):
        output_content_lines = self.output_content.split("\n")
        new_imports = self.build_imports().split("\n")
        output_content_lines[self.first_import_line_nbr : self.first_import_line_nbr] = new_imports
        self.output_content = "\n".join(output_content_lines)

    def replace_content(self):
        for regex, string in self.replacements:
            self.output_content = regex.sub(string, self.output_content)


def main():
    parser = argparse.ArgumentParser(description="Fix Nautobot Import Statements")
    parser.add_argument("filename", metavar="FILENAME", help="Path or glob of Python files to fix")

    args = parser.parse_args()
    filename = args.filename

    with open(filename, "r") as filedesc:
        data = filedesc.read()
    import_fix = NautobotImports(filename, data)
    content = import_fix.output_content

    with open(filename, "w") as filedesc:
        filedesc.write(content)
    if data != content:
        print("import successfully reordered for file: %s" % (filename))
    return 0


if __name__ == "__main__":
    main()
