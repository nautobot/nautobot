# refactor imports
import argparse
import os
import re

from isort import place_module


class NautobotImports:

    regexImport = re.compile(r"^import\s+(.*)\s*$")
    regexFromImport = re.compile(r"^from\s+(\S+)\s+import\s+(.*)\s*$")

    def __init__(self, filename, data):
        self.filename = filename
        self.data = data
        self.dirname = os.path.dirname(filename)
        self.python_library_path = self.dirname.replace("/", ".")
        self.enumerate_imports()

    def categorize_imports(self, imports):
        categories = {
            "stdlib": {},
            "nautobot": {},
            "other": {},
        }
        for package, names in imports.items():
            if package.startswith("nautobot") or package.startswith("."):
                categories["nautobot"][package] = names
            elif place_module(package) == "STDLIB":
                categories["stdlib"][package] = names
            else:
                categories["other"][package] = names

        self.imports = categories

    def build_imports(self, categorized_imports):
        output = ""
        for lib in ["stdlib", "other", "nautobot"]:
            for package in sorted(categorized_imports[lib].keys(), key=str.lower):
                names = ", ".join(sorted(categorized_imports[lib][package], key=str.lower))
                if names:
                    output += f"from {package} import {names}\n"
                else:
                    output += f"import {package}\n"
            if self.imports[lib]:
                output += "\n"
        output += "\n"
        return output

    def exec(self):
        print(self.build_imports(self.fix_imports()))
        return 1, ""

    def enumerate_imports(self):
        imports = {}
        multi_line = ""
        for line in self.data.split("\n"):

            # handle multi-line imports
            if multi_line:
                if re.match(r"^\s*\)?\s*$", line):
                    multi_line = ""
                    continue
                imports.setdefault(multi_line, [])
                for name in line.strip().split(","):
                    if name.strip() and name.strip() not in imports[multi_line]:
                        imports[multi_line].append(name.strip())

            # handle module imports
            match = self.regexImport.match(line)
            if match:
                if match.group(1) == "(":
                    raise Exception(f"unexpected multi-line import: {line}")
                for name in match.group(1).strip().split(","):
                    package = ".".join(name.strip().split(".")[0:-1])
                    module = name.strip().split(".")[-1].strip()
                    if package == "":
                        imports.setdefault(module, [])
                        continue
                    imports.setdefault(package, [])
                    if module not in imports[package]:
                        imports[package].append(module)

            # handle name imports
            match = self.regexFromImport.match(line)
            if match:
                package = match.group(1)
                if match.group(2) == "(":
                    multi_line = match.group(1)
                    continue
                for name in match.group(2).strip().split(","):
                    imports.setdefault(package, [])
                    if name.strip() not in imports[package]:
                        imports[package].append(name.strip())

        self.categorize_imports(imports)

    def fix_imports(self):
        fixed_imports = {}
        for package, names in self.imports["nautobot"].items():
            if package == ".":
                fixed_imports.setdefault(self.python_library_path, [])
                for name in names.split(","):
                    name = name.strip()
                    if name not in fixed_imports[self.python_library_path]:
                        fixed_imports[self.python_library_path].append(name)
                continue
            elif package.startswith("."):
                package = self.python_library_path + "." + package[1:]
            for name in names:
                name = name.strip()
                if os.path.exists(f"{self.dirname}/{name}.py") or os.path.exists(f"{self.dirname}/{name}/__init__.py"):
                    fixed_imports.setdefault(package, [])
                    if name not in fixed_imports[package]:
                        fixed_imports[package].append(name)
                else:
                    containing_module = ".".join(package.split(".")[:-1])
                    fixed_imports.setdefault(containing_module, [])
                    name = package.split(".")[-1]
                    if name not in fixed_imports[containing_module]:
                        fixed_imports[containing_module].append(name)
                    # TODO: keep track of these ones for regex replacement later

        return {"nautobot": fixed_imports, "stdlib": self.imports["stdlib"], "other": self.imports["other"]}


def main():
    parser = argparse.ArgumentParser(description="Fix Nautobot Import Statements")
    parser.add_argument("filename", metavar="FILENAME", help="Path or glob of Python files to fix")

    args = parser.parse_args()
    filename = args.filename

    with open(filename, "r") as filedesc:
        data = filedesc.read()
    res, content = NautobotImports(filename, data).exec()
    if not res:
        return 1

    # with open(filename, "w") as filedesc:
    #     filedesc.write(content)
    # if data != content:
    #     print("import successfully reordered for file: %s" % (filename))
    # return 0


if __name__ == "__main__":
    main()
