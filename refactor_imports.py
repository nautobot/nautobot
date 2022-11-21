# refactor imports
# find nautobot/appname/ -iname "*.py" -exec python refactor_imports.py {} \;
import argparse
import collections
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
        return f"from {self.package_name} import {self.name_str}"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return all((self.package_name == other.package_name, self.name == other.name))

    def __hash__(self):
        return hash((self.package_name, self._name, self.alias))

    def __lt__(self, other):
        if self.package_name != other.package_name:
            return self.package_name.lower() < other.package_name.lower()
        if self._name == TopLevelImport:
            return True
        if other._name == TopLevelImport:
            return False
        return self._name.lower() < other._name.lower()


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
        self.nautobot_app = filename.split("/").pop(filename.split("/").index("nautobot") + 1)
        self.enumerate_imports()
        self.fix_imports()
        self.generate_aliases()
        self.replace_content()
        self.insert_new_imports()

    def generate_aliases(self):
        """find imports that need to be aliased"""
        all_imports = self.imports["nautobot"] + self.imports["stdlib"] + self.imports["other"]
        names = collections.Counter([x.name for x in all_imports if x.name != TopLevelImport])
        duplicates = [k for k, v in names.items() if v > 1]
        duplicate_imports = [i for i in all_imports if i.name in duplicates]
        for duplicate in duplicate_imports:
            if duplicate.package_name.startswith(f"nautobot.{self.nautobot_app}"):
                continue
            if duplicate.package_name.startswith("nautobot"):
                nautobot_app = duplicate.package_name.split(".")[1]
                duplicate.alias = f"{nautobot_app}_{duplicate._name}"
            else:
                top_level_package = duplicate.package_name.split(".")[0]
                duplicate.alias = f"{top_level_package}_{duplicate._name}"

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

    def _build_output_line(self, lines):
        if not lines:
            return ""
        output = []
        names = ", ".join([n.name_str for n in lines if not n.alias])
        if names:
            output.append(f"from {lines[0].package_name} import {names}\n")
        for name in [n for n in lines if n.alias]:
            output.append(f"from {name.package_name} import {name.name_str}\n")
        return "".join(sorted(output, key=str.lower))

    def build_imports(self):
        output = ""
        for category in ["stdlib", "other", "nautobot"]:
            line_queue = []
            for imported_name in sorted(self.imports[category]):
                if imported_name.name == TopLevelImport:
                    output += self._build_output_line(line_queue)
                    line_queue = []
                    output += f"import {imported_name.package_name}\n"
                    continue
                elif line_queue and imported_name.package_name != line_queue[0].package_name:
                    output += self._build_output_line(line_queue)
                    line_queue = []
                line_queue.append(imported_name)
            if line_queue:
                output += self._build_output_line(line_queue)
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
                    self.add_import(multi_line, name)

            # handle module imports (import os, re)
            match = self.regexImport.match(line)
            if match:
                if match.group(1) == "(":
                    raise Exception(f"unexpected multi-line import: {line}")
                for name in match.group(1).strip().split(","):
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
        for import_obj in self.imports["nautobot"].copy():
            if import_obj.package_name == ".":
                import_obj.package_name = self.python_library_path
                continue
            elif import_obj.package_name.startswith("."):
                import_obj.package_name = self.python_library_path + "." + import_obj.package_name[1:]

            # don't try to fix wildcard imports
            if import_obj.name == "*":
                continue

            if import_obj.name != TopLevelImport and import_obj.package_name.startswith("nautobot"):
                package_path = import_obj.package_name[9:].replace(".", "/")
                path = f"{self.nautobot_base}/{package_path}/{import_obj._name}"
                if not (os.path.exists(f"{path}.py") or os.path.exists(f"{path}/__init__.py")):
                    old_name = import_obj.name
                    containing_module = ".".join(import_obj.package_name.split(".")[:-1])
                    name = import_obj.package_name.split(".")[-1]
                    # deduplicate
                    self.imports["nautobot"].remove(import_obj)
                    new_import_obj = ImportedName(containing_module, name)
                    if new_import_obj not in self.imports["nautobot"]:
                        self.imports["nautobot"].append(new_import_obj)
                        i = -1
                    else:
                        i = self.imports["nautobot"].index(new_import_obj)

                    # keep track of these ones for regex replacement later
                    self.replacements.append((self.imports["nautobot"][i], old_name))

    def insert_new_imports(self):
        output_content_lines = self.output_content.split("\n")
        new_imports = self.build_imports().split("\n")
        output_content_lines[self.first_import_line_nbr : self.first_import_line_nbr] = new_imports
        self.output_content = "\n".join(output_content_lines)
        self.output_content = re.sub(r"\n\n\n\n+", r"\n\n\n", self.output_content)
        self.output_content = re.sub(r"\n+$", r"\n", self.output_content)

    def replace_content(self):
        for import_obj, old_name in self.replacements:
            re_old = re.escape(old_name) + r"(,|\s|$|\(|\)|\.|:|\]|\[)"
            self.output_content = re.sub(re_old, f"{import_obj.name}.{old_name}" + r"\1", self.output_content)


def main():
    parser = argparse.ArgumentParser(description="Fix Nautobot Import Statements")
    parser.add_argument("filename", metavar="FILENAME", help="Path or glob of Python files to fix")

    args = parser.parse_args()
    filename = args.filename
    if os.path.basename(filename) == "__init__.py":
        print(f"skipped {filename}")
        exit()

    with open(filename, "r") as filedesc:
        data = filedesc.read()
    import_fix = NautobotImports(filename, data)
    content = import_fix.output_content

    if re.sub(r"\s", "", data) != re.sub(r"\s", "", content):
        with open(filename, "w") as filedesc:
            filedesc.write(content)
        print(f"imports fixed for file: {filename}")
    else:
        print(f"no changes made in file: {filename}")


if __name__ == "__main__":
    main()
