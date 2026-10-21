"""The dependency rule: the domain imports only itself; the application imports
the domain and itself. Neither imports Django, the ORM apps or the adapters."""
import ast
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FORBIDDEN = {
    "domain": ("django", "rest_framework", "celery", "neurovault."),
    "application": ("django", "rest_framework", "celery", "neurovault.apps", "neurovault.api",
                    "neurovault.adapters", "neurovault.bootstrap"),
}
ALLOWED_INTERNAL = {"domain": ("neurovault.domain",), "application": ()}


def imports(path):
    with open(path) as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


class DependencyRule(unittest.TestCase):
    def test_layers(self):
        for layer, forbidden in FORBIDDEN.items():
            for dirpath, _, files in os.walk(os.path.join(ROOT, layer)):
                if "tests" in dirpath.split(os.sep):
                    continue
                for name in files:
                    if not name.endswith(".py"):
                        continue
                    path = os.path.join(dirpath, name)
                    for module in imports(path):
                        if module.startswith(ALLOWED_INTERNAL[layer]):
                            continue
                        with self.subTest(path=path, module=module):
                            self.assertFalse(module.startswith(forbidden), module)
