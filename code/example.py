import ast
import os
import markdown2
from datetime import datetime


class CodeAnalyzer(ast.NodeVisitor):
    """Analyze a Python file and extract documentation details."""

    def __init__(self, file_path):
        self.file_path = file_path
        self.tree = None
        self.imports = []
        self.classes = []
        self.functions = []

    def parse(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            source = f.read()
        self.tree = ast.parse(source)
        self.visit(self.tree)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(f"{node.module} (from)")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_info = {
            "name": node.name,
            "lineno": node.lineno,
            "docstring": ast.get_docstring(node),
            "methods": []
        }
        for body_item in node.body:
            if isinstance(body_item, ast.FunctionDef):
                method_info = {
                    "name": body_item.name,
                    "args": [a.arg for a in body_item.args.args],
                    "lineno": body_item.lineno,
                    "docstring": ast.get_docstring(body_item)
                }
                class_info["methods"].append(method_info)
        self.classes.append(class_info)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Skip class methods (handled separately)
        if not isinstance(getattr(node, "parent", None), ast.ClassDef):
            func_info = {
                "name": node.name,
                "args": [a.arg for a in node.args.args],
                "lineno": node.lineno,
                "docstring": ast.get_docstring(node)
            }
            self.functions.append(func_info)
        self.generic_visit(node)


def attach_parents(node):
    """Attach parent references to nodes (for class detection)."""
    for child in ast.iter_child_nodes(node):
        child.parent = node
        attach_parents(child)


class DocumentationBuilder:
    """Generates Markdown and HTML documentation from parsed code."""

    def __init__(self, analyzer):
        self.analyzer = analyzer

    def generate_markdown(self):
        lines = []
        lines.append(f"# Documentation for `{os.path.basename(self.analyzer.file_path)}`\n")
        lines.append(f"_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n")

        # Imports
        if self.analyzer.imports:
            lines.append("## Imports\n")
            for imp in self.analyzer.imports:
                lines.append(f"- {imp}")
            lines.append("\n")

        # Classes
        for cls in self.analyzer.classes:
            lines.append(f"## Class: `{cls['name']}` (line {cls['lineno']})\n")
            if cls["docstring"]:
                lines.append(f"> {cls['docstring']}\n")
            if cls["methods"]:
                lines.append("### Methods:\n")
                for m in cls["methods"]:
                    lines.append(f"- **{m['name']}({', '.join(m['args'])})** — line {m['lineno']}")
                    if m["docstring"]:
                        lines.append(f"  - _{m['docstring']}_")
                lines.append("\n")

        # Functions
        if self.analyzer.functions:
            lines.append("## Functions\n")
            for func in self.analyzer.functions:
                lines.append(f"- **{func['name']}({', '.join(func['args'])})** — line {func['lineno']}")
                if func["docstring"]:
                    lines.append(f"  - _{func['docstring']}_")
            lines.append("\n")

        return "\n".join(lines)

    def export(self):
        md_text = self.generate_markdown()
        md_file = self.analyzer.file_path.replace(".py", "_doc.md")
        html_file = self.analyzer.file_path.replace(".py", "_doc.html")

        # Write Markdown
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_text)

        # Write HTML
        html = markdown2.markdown(md_text)
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Markdown saved to {md_file}")
        print(f"HTML saved to {html_file}")


if __name__ == "__main__":
    path = input("Enter Python file path: ").strip()
    if not os.path.exists(path):
        print("File not found.")
        exit()

    analyzer = CodeAnalyzer(path)
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    attach_parents(tree)
    analyzer.tree = tree
    analyzer.visit(tree)

    doc = DocumentationBuilder(analyzer)
    doc.export()
