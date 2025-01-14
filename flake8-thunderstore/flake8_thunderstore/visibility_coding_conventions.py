import ast

from flake8_plugin_utils import Plugin


class VisibilityCodingConventions(Plugin):
    name = "visibility-coding-conventions"
    version = "1.0.1"

    visibility_classes = ["PackageListing", "PackageVersion"]
    safe_functions = ["public_list", "system", "get", "create", "get_or_create"]
    excluded_filepaths = ["/migrations/", "/tests/", "/commands/", "/conftest.py"]

    def __init__(self, tree: ast.AST, filename: str) -> None:
        self.tree = tree
        self.filename = filename

    def run(self):
        if any(excluded in self.filename for excluded in self.excluded_filepaths):
            return

        for node in ast.walk(self.tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "objects"
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id in self.visibility_classes
                and node.attr not in self.safe_functions
            ):
                yield (
                    node.lineno,
                    node.col_offset,
                    f"VIS753 {node.value.value.id}.objects.{node.attr} is unsafe; Objects with visibility should always be called with .public_list() or .system())",
                    type(self),
                )
