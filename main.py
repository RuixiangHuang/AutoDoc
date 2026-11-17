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
        self.source_code = source_code
        self.source_lines = source_code.split('\n') if source_code else []
        self.current_class = None
        self.current_function = None
        self.classes = []
        self.functions = []
        self.variables = []
        self.api_decorators = {}

    # ----- Classes -----
    def visit_ClassDef(self, node):
        start, end = self._node_span(node)
        code_snippet = self._extract_code_snippet(start, end)
        
        max_lines = 1000
        if end - start > max_lines:
            code_snippet = self._extract_code_snippet(start, start + max_lines)
            end = start + max_lines
        
        docstring = ast.get_docstring(node)
        self.classes.append((node.name, self.file_name, start, end, code_snippet, docstring))
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    # ----- Functions -----
    def visit_FunctionDef(self, node):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)

    def _visit_function(self, node):
        skip_functions = {
            "__init__", "__str__", "__repr__", "__eq__", "__ne__", "__hash__",
            "__lt__", "__le__", "__gt__", "__ge__", "__del__", "__new__",
            "__getattr__", "__setattr__", "__delattr__", "__getattribute__",
            "__call__", "__len__", "__getitem__", "__setitem__", "__delitem__",
            "__iter__", "__next__", "__contains__", "__bool__", "__int__",
            "__float__", "__complex__", "__index__", "__enter__", "__exit__"
        }
        
        if node.name not in skip_functions:
            start, end = self._node_span(node)
            code_snippet = self._extract_code_snippet(start, end)
            
            max_lines = 500
            if end - start > max_lines:
                code_snippet = self._extract_code_snippet(start, start + max_lines)
                end = start + max_lines
            
            docstring = ast.get_docstring(node)
            
            decorators = self._extract_decorators(node)
            
            self.functions.append((
                node.name,
                self.file_name,
                self.current_class if self.current_class else "",
                start,
                end,
                code_snippet,
                docstring,
                decorators
            ))
        prev_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_function
    
    def _extract_decorators(self, node):
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    decorator_name = f"{self._get_attr_name(decorator.func)}"
                elif isinstance(decorator.func, ast.Name):
                    decorator_name = decorator.func.id
                else:
                    decorator_name = "unknown"
                
                args = []
                for arg in decorator.args:
                    if isinstance(arg, ast.Constant):
                        args.append(str(arg.value))
                    elif isinstance(arg, ast.Str):  # Python < 3.8
                        args.append(arg.s)
                
                decorators.append({
                    "name": decorator_name,
                    "args": args
                })
            elif isinstance(decorator, ast.Attribute):
                decorators.append({
                    "name": self._get_attr_name(decorator),
                    "args": []
                })
            elif isinstance(decorator, ast.Name):
                decorators.append({
                    "name": decorator.id,
                    "args": []
                })
        return decorators
    
    def _get_attr_name(self, node):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
            elif isinstance(node.value, ast.Attribute):
                return f"{self._get_attr_name(node.value)}.{node.attr}"
        return "unknown"

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
    
    def visit_AnnAssign(self, node):
        # Annotated assignment: `x: int = 0` or `self.x: int = 0`
        target = node.target
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
            name = target.attr
        elif isinstance(target, ast.Name):
            name = target.id
        else:
            name = None
        if name:
            self.variables.append((
                name,
                self.file_name,
                self.current_class if self.current_class else "",
                self.current_function if self.current_function else "",
                node.lineno
            ))
        self.generic_visit(node)

    @staticmethod
    def _node_span(node):
        """(start, end) lines of a def/class, including decorators and closing lines."""
        start = min([d.lineno for d in node.decorator_list] + [node.lineno])
        end = getattr(node, "end_lineno", None) or max(
            (n.lineno for n in ast.walk(node) if hasattr(n, "lineno")), default=node.lineno
        )
        return start, end

    def _extract_code_snippet(self, start_line: int, end_line: int) -> str:
        if not self.source_lines:
            return ""
        start_idx = max(0, start_line - 1)
        end_idx = min(len(self.source_lines), end_line)
        return '\n'.join(self.source_lines[start_idx:end_idx])

def extract_code_elements(file_path, display_name=None):
    """
    Parse a Python file. `display_name` is how the file is identified in the
    results (defaults to its basename); scan_directory passes the path
    relative to the scan root so same-named files in different folders stay distinct.
    """
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'gbk', 'gb2312']
    source = None
    
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                source = f.read()
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Cannot read file {file_path}: {str(e)}")
            return [], [], []
    
    if source is None:
        print(f"Cannot decode file in path: {file_path}, skip")
        return [], [], []
    
    try:
        tree = ast.parse(source)
        analyzer = CodeAnalyzer(display_name or os.path.basename(file_path), file_path=file_path, source_code=source)
        analyzer.visit(tree)
        return analyzer.classes, analyzer.functions, analyzer.variables
    except SyntaxError as e:
        print(f"File {file_path} has syntax error, skip: {str(e)}")
        return [], [], []
    except Exception as e:
        print(f"Analysis file {file_path} error, skip: {str(e)}")
        return [], [], []

def scan_directory(directory, file_filter=None):
    all_classes = []
    all_functions = []
    all_variables = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                # Filter on the path relative to the scan root, so keywords that
                # happen to appear in the root itself (e.g. ~/my_api_project) don't match everything
                rel_path = os.path.relpath(path, directory)
                if file_filter and not file_filter(rel_path, file):
                    continue
                cls, funcs, vars_ = extract_code_elements(path, display_name=rel_path)
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
    init_database()
    clear_database()
    
    code_dir = "code"
    classes, functions, variables = scan_directory(code_dir)

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
    
    print("\nCode analysis completed! Data saved to SQLite database.")
