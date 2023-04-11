import os.path
import re

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from tabulate import tabulate
import yaml


SYNTAX = re.compile(r"^(\s*)\{data-table\s+(\S+)\}$")


class NautobotDataTablesPreprocessor(Preprocessor):
    """Look for {data-table filename} in the markdown."""

    def run(self, lines):
        new_lines = []
        for line in lines:
            match = SYNTAX.match(line)
            if not match:
                new_lines.append(line)
                continue
            indent = match.group(1)
            filename = match.group(2)
            new_lines += self.make_table(filename, indent=indent)

        return new_lines

    def make_table(self, filename, indent=""):
        if not os.path.isabs(filename):
            filename = os.path.normpath(os.path.join(os.path.dirname(__file__), filename))
        with open(filename, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        return [indent + line for line in tabulate(data, headers="keys", tablefmt="github").split("\n")]


class NautobotDataTables(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(NautobotDataTablesPreprocessor(md), "data-tables", 100)


def makeExtension(*args, **kwargs):
    return NautobotDataTables(**kwargs)
