import ast
import os

import pytest

visibility_classes = ["PackageListing", "PackageVersion"]

safe_functions = ["public_list", "system", "get", "create", "get_or_create"]

excluded_filepaths = ["/migrations/", "/tests/", "/commands/", "/conftest.py"]


def find_violations(tree, file_path):
    violations = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "objects"
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id in visibility_classes
            and node.attr not in safe_functions
        ):
            violations.append(
                f"'{node.value.value.id}.objects.{node.attr}' at line {node.lineno} of '{file_path}'"
            )
    return violations


@pytest.mark.django_db
def test_visibility_mixin_usage():
    violations = []

    for root, _, files in os.walk("../app/"):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                if not any(excluded in file_path for excluded in excluded_filepaths):
                    with open(file_path, "r", encoding="utf-8") as f:
                        try:
                            tree = ast.parse(f.read(), filename=file_path)

                            violations.extend(find_violations(tree, file_path))
                        except SyntaxError as e:
                            pytest.fail(f"Syntax error in {file_path}: {e}")

    if violations:
        pytest.fail(
            "Found unsafe usage of visibility objects:\n"
            + "\n".join(violations)
            + "\nObjects with visibility should always be called with .public_list() or .system()"
        )
