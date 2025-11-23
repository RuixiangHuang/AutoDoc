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
        # 用于存储接口相关信息
        self.api_decorators = {}  # function_name -> [decorators]

    # ----- Classes -----
    def visit_ClassDef(self, node):
        start = node.lineno
        end = max([n.lineno for n in ast.walk(node) if hasattr(n, "lineno")], default=start)
        # 提取源代码片段
        code_snippet = self._extract_code_snippet(start, end)
        
        # 限制代码片段大小（最多 1000 行，避免 context window 溢出）
        max_lines = 1000
        if end - start > max_lines:
            # 如果代码太长，只取前 max_lines 行
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
        # 过滤掉 Python 内置的魔法方法和基础方法
        skip_functions = {
            "__init__", "__str__", "__repr__", "__eq__", "__ne__", "__hash__",
            "__lt__", "__le__", "__gt__", "__ge__", "__del__", "__new__",
            "__getattr__", "__setattr__", "__delattr__", "__getattribute__",
            "__call__", "__len__", "__getitem__", "__setitem__", "__delitem__",
            "__iter__", "__next__", "__contains__", "__bool__", "__int__",
            "__float__", "__complex__", "__index__", "__enter__", "__exit__"
        }
        
        if node.name not in skip_functions:
            start = node.lineno
            end = max([n.lineno for n in ast.walk(node) if hasattr(n, "lineno")], default=start)
            # 提取源代码片段
            code_snippet = self._extract_code_snippet(start, end)
            
            # 限制代码片段大小（最多 500 行，避免 context window 溢出）
            max_lines = 500
            if end - start > max_lines:
                # 如果代码太长，只取前 max_lines 行
                code_snippet = self._extract_code_snippet(start, start + max_lines)
                end = start + max_lines
            
            docstring = ast.get_docstring(node)
            
            # 提取装饰器信息（用于识别 API 接口）
            decorators = self._extract_decorators(node)
            
            self.functions.append((
                node.name,
                self.file_name,
                self.current_class if self.current_class else "",
                start,
                end,
                code_snippet,
                docstring,
                decorators  # 添加装饰器信息
            ))
        prev_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_function
    
    def _extract_decorators(self, node):
        """提取函数的装饰器信息"""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                # 处理 @app.route('/path') 这样的装饰器
                if isinstance(decorator.func, ast.Attribute):
                    decorator_name = f"{self._get_attr_name(decorator.func)}"
                elif isinstance(decorator.func, ast.Name):
                    decorator_name = decorator.func.id
                else:
                    decorator_name = "unknown"
                
                # 提取参数
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
        """获取属性名称，如 app.route -> app.route"""
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
    
    def _extract_code_snippet(self, start_line: int, end_line: int) -> str:
        """根据行号范围提取源代码片段"""
        if not self.source_lines:
            return ""
        # AST 行号从 1 开始，列表索引从 0 开始
        start_idx = max(0, start_line - 1)
        end_idx = min(len(self.source_lines), end_line)
        return '\n'.join(self.source_lines[start_idx:end_idx])

def extract_code_elements(file_path):
    """提取代码元素，支持多种编码格式"""
    # 尝试多种编码方式
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
            print(f"⚠️  无法读取文件 {file_path}: {str(e)}")
            return [], [], []
    
    if source is None:
        print(f"⚠️  无法解码文件 {file_path}，跳过该文件")
        return [], [], []
    
    try:
        tree = ast.parse(source)
        analyzer = CodeAnalyzer(os.path.basename(file_path), file_path=file_path, source_code=source)
        analyzer.visit(tree)
        return analyzer.classes, analyzer.functions, analyzer.variables
    except SyntaxError as e:
        print(f"⚠️  文件 {file_path} 有语法错误，跳过: {str(e)}")
        return [], [], []
    except Exception as e:
        print(f"⚠️  分析文件 {file_path} 时出错，跳过: {str(e)}")
        return [], [], []

def scan_directory(directory, file_filter=None):
    """
    扫描目录中的 Python 文件
    
    Args:
        directory: 要扫描的目录
        file_filter: 文件过滤函数，接收 (file_path, file_name) 参数，返回 True 表示包含该文件
    """
    all_classes = []
    all_functions = []
    all_variables = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                # 应用文件过滤
                if file_filter and not file_filter(path, file):
                    continue
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
