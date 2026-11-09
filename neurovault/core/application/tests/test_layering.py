"""The dependency rule (docs/design/0001 §2), checked on every import statement.

- core.domain imports the standard library, numpy, nibabel and nilearn, and
  itself.
- core.application imports the standard library, core.domain and itself;
  its tests (fakes included) may also use numpy and nibabel.
- The web and API adapters do not import each other; what both need lives in
  neurovault.adapters.http or another adapter.

Relative imports are resolved to absolute module names before checking.
"""
import ast
import os
import sys
import unittest

PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCIENTIFIC = ("numpy", "nibabel", "nilearn", "scipy")
CORE_RULES = {
    "neurovault.core.domain": SCIENTIFIC + ("neurovault.core.domain",),
    "neurovault.core.application": ("neurovault.core.domain", "neurovault.core.application"),
}
TEST_EXTRAS = ("numpy", "nibabel")
ADAPTER_RULES = {
    "neurovault.adapters.api": ("neurovault.adapters.web",),
    "neurovault.adapters.web": ("neurovault.adapters.api",),
}


def module_name(path):
    rel = os.path.relpath(path, os.path.dirname(PACKAGE_ROOT))[: -len(".py")]
    parts = rel.split(os.sep)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def imports(path):
    """Absolute names of every module `path` imports."""
    name = module_name(path)
    package = name if path.endswith("__init__.py") else name.rsplit(".", 1)[0]
    with open(path) as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - (node.level - 1)]
                yield ".".join(base + ([node.module] if node.module else []))
            else:
                yield node.module


def python_files(package):
    root = os.path.join(os.path.dirname(PACKAGE_ROOT), *package.split("."))
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(dirpath, f)


def is_within(module, prefixes):
    return any(module == p or module.startswith(p + ".") for p in prefixes)


class DependencyRule(unittest.TestCase):
    def test_core_imports_only_the_standard_library_science_and_inner_layers(self):
        for package, allowed in CORE_RULES.items():
            for path in python_files(package):
                in_tests = os.sep + "tests" + os.sep in path
                for module in imports(path):
                    top = module.split(".")[0]
                    if top in sys.stdlib_module_names or top == "__future__":
                        continue
                    ok = allowed + (TEST_EXTRAS + ("neurovault.core.application",) if in_tests else ())
                    with self.subTest(path=os.path.relpath(path, PACKAGE_ROOT), module=module):
                        self.assertTrue(is_within(module, ok), module)

    def test_web_and_api_adapters_do_not_import_each_other(self):
        for package, forbidden in ADAPTER_RULES.items():
            for path in python_files(package):
                if os.sep + "tests" + os.sep in path or os.sep + "management" + os.sep in path:
                    continue
                for module in imports(path):
                    with self.subTest(path=os.path.relpath(path, PACKAGE_ROOT), module=module):
                        self.assertFalse(is_within(module, forbidden), module)
