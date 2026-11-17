"""
Regression tests for code analysis and documentation correctness.

Run with:  python -m unittest discover -s tests
(Uses only the standard library; no LLM, vector store or network needed.)
"""
import os
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import extract_code_elements, scan_directory  # noqa: E402
from elements import element_id, is_same_element  # noqa: E402


SAMPLE = textwrap.dedent('''\
    from fastapi import APIRouter
    router = APIRouter()

    @router.get("/users")
    async def list_users():
        return [1, 2]

    class UserView:
        def get(self):
            return "user"

    class OrderView:
        def get(self):
            return {
                "a": 1,
            }

    count: int = 0
''')


def _write(directory, rel_path, content):
    path = os.path.join(directory, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = _write(self.tmp.name, "sample.py", SAMPLE)
        self.classes, self.functions, self.variables = extract_code_elements(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def _func(self, name, class_name=""):
        matches = [f for f in self.functions if f[0] == name and f[2] == class_name]
        self.assertEqual(len(matches), 1, f"expected exactly one {class_name}.{name}")
        return matches[0]

    def test_async_functions_are_extracted(self):
        func = self._func("list_users")
        self.assertIn("async def list_users", func[5])
        self.assertEqual(func[7], [{"name": "router.get", "args": ["/users"]}])

    def test_snippet_includes_decorators(self):
        func = self._func("list_users")
        self.assertEqual(func[3], 4)  # starts at the decorator line
        self.assertTrue(func[5].startswith('@router.get("/users")'))

    def test_snippet_includes_closing_lines(self):
        func = self._func("get", "OrderView")
        self.assertEqual(func[4], 16)
        self.assertTrue(func[5].rstrip().endswith("}"))
        order_view = [c for c in self.classes if c[0] == "OrderView"][0]
        self.assertEqual(order_view[3], 16)

    def test_annotated_variables_are_extracted(self):
        self.assertIn("count", [v[0] for v in self.variables])


class ScanDirectoryTests(unittest.TestCase):
    def setUp(self):
        # The root itself contains "api" — it must not make every file match.
        self.tmp = tempfile.TemporaryDirectory(suffix="_api_project")
        self.root = self.tmp.name
        _write(self.root, "pkg_a/views.py", "def a():\n    pass\n")
        _write(self.root, "pkg_b/views.py", "def b():\n    pass\n")
        _write(self.root, "routes/users.py", "def c():\n    pass\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_identity_is_relative_path(self):
        _, functions, _ = scan_directory(self.root)
        files = sorted(f[1] for f in functions)
        self.assertEqual(files, sorted([
            os.path.join("pkg_a", "views.py"),
            os.path.join("pkg_b", "views.py"),
            os.path.join("routes", "users.py"),
        ]))

    def test_filter_ignores_scan_root_path(self):
        def only_routes(file_path, file_name):
            return "route" in file_path.lower() or "api" in file_path.lower()

        _, functions, _ = scan_directory(self.root, file_filter=only_routes)
        self.assertEqual([f[0] for f in functions], ["c"])


class ElementIdTests(unittest.TestCase):
    def test_same_method_name_in_different_classes_is_unique(self):
        a = element_id("views.py", "function", "get", "UserView")
        b = element_id("views.py", "function", "get", "OrderView")
        self.assertNotEqual(a, b)

    def test_same_name_in_different_files_is_unique(self):
        a = element_id("pkg_a/views.py", "function", "get", "")
        b = element_id("pkg_b/views.py", "function", "get", "")
        self.assertNotEqual(a, b)

    def test_is_same_element_matches_on_metadata(self):
        meta = {"type": "function", "name": "get", "file": "views.py", "class_name": "UserView"}
        self.assertTrue(is_same_element(meta, "views.py", "function", "get", "UserView"))
        self.assertFalse(is_same_element(meta, "views.py", "function", "get", "OrderView"))


class DocumentGeneratorTests(unittest.TestCase):
    def test_methods_with_same_name_get_their_own_explanation(self):
        from document_generator import DocumentGenerator

        functions = [
            ("get", "views.py", "UserView", 2, 3, "def get(self): ...", None, []),
            ("get", "views.py", "OrderView", 6, 7, "def get(self): ...", None, []),
        ]
        explanations = {
            element_id("views.py", "function", "get", "UserView"): "EXPLAIN-USER",
            element_id("views.py", "function", "get", "OrderView"): "EXPLAIN-ORDER",
        }
        md = DocumentGenerator().generate_markdown(
            project_name="p",
            file_structure=["views.py"],
            code_data={"classes": [], "functions": functions, "variables": []},
            explanations=explanations,
        )
        self.assertIn("EXPLAIN-USER", md)
        self.assertIn("EXPLAIN-ORDER", md)


if __name__ == "__main__":
    unittest.main()
