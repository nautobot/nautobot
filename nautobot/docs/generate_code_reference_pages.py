"""Generate code reference pages."""

from pathlib import Path

import mkdocs_gen_files

for file_path in sorted(Path("nautobot", "apps").rglob("*.py")):
    module_path = file_path.with_suffix("")
    doc_path = file_path.with_suffix(".md")
    full_doc_path = Path("code-reference", doc_path)

    parts = list(module_path.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        identifier = ".".join(parts)
        print(f"::: {identifier}", file=fd)

    mkdocs_gen_files.set_edit_path(full_doc_path, file_path)
