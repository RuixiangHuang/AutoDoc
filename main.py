import ast
import os
import csv

OUTPUT_DIR = "data_clean"
os.makedirs(OUTPUT_DIR, exist_ok=True)  # Create folder if it doesn't exist

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self, file_name):
        self.file_name = file_name
        self.current_class = None
        self.current_function = None
        self.classes = []
        self.functions = []
        self.variables = []

    # ----- Classes -----
    def visit_ClassDef(self, node):
        start = node.lineno
        end = max([n.lineno for n in ast.walk(node) if hasattr(n, "lineno")], default=start)
        self.classes.append((node.name, self.file_name, start, end))
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    # ----- Functions -----
    def visit_FunctionDef(self, node):
        if node.name != "__init__":
            start = node.lineno
            end = max([n.lineno for n in ast.walk(node) if hasattr(n, "lineno")], default=start)
            self.functions.append((
                node.name,
                self.file_name,
                self.current_class if self.current_class else "",
                start,
                end
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

def extract_code_elements(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    analyzer = CodeAnalyzer(os.path.basename(file_path))
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
    print(f"Saved {len(data)} entries to {filepath}")

if __name__ == "__main__":
    code_dir = "code"  # change to your target directory
    classes, functions, variables = scan_directory(code_dir)

    save_to_csv(classes, ["Class Name", "File", "Start Line", "End Line"], "classes.csv")
    save_to_csv(functions, ["Function Name", "File", "Class Name", "Start Line", "End Line"], "functions.csv")
    save_to_csv(variables, ["Variable Name", "File", "Class Name", "Function Name", "Line Number"], "variables.csv")
