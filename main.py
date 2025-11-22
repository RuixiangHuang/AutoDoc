import ast
import os
import csv
from database import init_database, clear_database, save_classes, save_functions, save_variables

OUTPUT_DIR = "data_clean"
os.makedirs(OUTPUT_DIR, exist_ok=True)  # Create folder if it doesn't exist

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self, file_name, file_path=None, source_code=None):
        self.file_name = file_name
        self.file_path = file_path
        self.source_code = source_code  # 完整的源代码
        self.source_lines = source_code.split('\n') if source_code else []
        self.current_class = None
        self.current_function = None
        self.classes = []
        self.functions = []
        self.variables = []

    # ----- Classes -----
    def visit_ClassDef(self, node):
        start = node.lineno
        end = max([n.lineno for n in ast.walk(node) if hasattr(n, "lineno")], default=start)
        # 提取源代码片段
        code_snippet = self._extract_code_snippet(start, end)
        docstring = ast.get_docstring(node)
        self.classes.append((node.name, self.file_name, start, end, code_snippet, docstring))
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    # ----- Functions -----
    def visit_FunctionDef(self, node):
        if node.name != "__init__":
            start = node.lineno
            end = max([n.lineno for n in ast.walk(node) if hasattr(n, "lineno")], default=start)
            # 提取源代码片段
            code_snippet = self._extract_code_snippet(start, end)
            docstring = ast.get_docstring(node)
            self.functions.append((
                node.name,
                self.file_name,
                self.current_class if self.current_class else "",
                start,
                end,
                code_snippet,
                docstring
            ))
        prev_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_function

    # ----- Variables -----
    def visit_Assign(self, node):
        for target in node.targets:
            # Instance variable: self.x
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                self.variables.append((
                    target.attr,
                    self.file_name,
                    self.current_class if self.current_class else "",
                    self.current_function if self.current_function else "",
                    node.lineno
                ))
            # Normal variables
            elif isinstance(target, ast.Name):
                self.variables.append((
                    target.id,
                    self.file_name,
                    self.current_class if self.current_class else "",
                    self.current_function if self.current_function else "",
                    node.lineno
                ))
        self.generic_visit(node)
    
    def _extract_code_snippet(self, start_line: int, end_line: int) -> str:
        """根据行号范围提取源代码片段"""
        if not self.source_lines:
            return ""
        # AST 行号从 1 开始，列表索引从 0 开始
        start_idx = max(0, start_line - 1)
        end_idx = min(len(self.source_lines), end_line)
        return '\n'.join(self.source_lines[start_idx:end_idx])

def extract_code_elements(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    analyzer = CodeAnalyzer(os.path.basename(file_path), file_path=file_path, source_code=source)
    analyzer.visit(tree)
    return analyzer.classes, analyzer.functions, analyzer.variables

def scan_directory(directory):
    all_classes = []
    all_functions = []
    all_variables = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                cls, funcs, vars_ = extract_code_elements(path)
                all_classes.extend(cls)
                all_functions.extend(funcs)
                all_variables.extend(vars_)
    return all_classes, all_functions, all_variables

def save_to_csv(data, columns, filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(data)
    print(f"✅ Saved {len(data)} entries to {filepath}")

if __name__ == "__main__":
    init_database()
    clear_database()
    
    code_dir = "code"
    classes, functions, variables = scan_directory(code_dir)

    # 只保存前4个元素到数据库（保持兼容性）
    classes_for_db = [(c[0], c[1], c[2], c[3]) for c in classes]
    functions_for_db = [(f[0], f[1], f[2], f[3], f[4]) for f in functions]
    
    save_classes(classes_for_db)
    save_functions(functions_for_db)
    save_variables(variables)
    
    export_csv = input("\nExport to CSV files as well? (y/n, default n): ").strip().lower() == 'y'
    if export_csv:
        save_to_csv(classes_for_db, ["Class Name", "File", "Start Line", "End Line"], "classes.csv")
        save_to_csv(functions_for_db, ["Function Name", "File", "Class Name", "Start Line", "End Line"], "functions.csv")
        save_to_csv(variables, ["Variable Name", "File", "Class Name", "Function Name", "Line Number"], "variables.csv")
    
    print("\n✅ Code analysis completed! Data saved to SQLite database.")
