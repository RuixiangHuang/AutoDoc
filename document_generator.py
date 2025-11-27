import os
from datetime import datetime
from typing import Dict, List, Optional
from markdown import markdown

# 设置 WeasyPrint 需要的库路径（macOS Homebrew）
if os.path.exists("/opt/homebrew/lib"):
    os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")
    if "DYLD_LIBRARY_PATH" in os.environ and "/opt/homebrew/lib" not in os.environ["DYLD_LIBRARY_PATH"]:
        os.environ["DYLD_LIBRARY_PATH"] = f"/opt/homebrew/lib:{os.environ['DYLD_LIBRARY_PATH']}"

# WeasyPrint 延迟导入，避免在模块加载时就失败
# 捕获 ImportError 和 OSError（系统库缺失时）
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError, Exception) as e:
    WEASYPRINT_AVAILABLE = False
    HTML = None
    # 静默失败，在需要时再提示用户


class DocumentGenerator:
    """生成 Markdown 和 PDF 文档"""
    
    def __init__(self, language: str = "en"):
        """
        Initialize document generator
        
        Args:
            language: Language selection, "zh" for Chinese, "en" for English
        """
        self.language = language
        
        # 中英文文本
        self.texts = {
            "zh": {
                "title": "项目代码文档",
                "generated_on": "生成时间",
                "project_structure": "项目结构",
                "file": "文件",
                "class": "类",
                "function": "函数",
                "variables": "变量",
                "source_code": "源代码",
                "explanation": "说明",
                "docstring": "文档字符串",
                "location": "位置",
                "line": "行",
                "no_explanation": "暂无说明",
                "decorator": "接口装饰器"
            },
            "en": {
                "title": "Project Code Documentation",
                "generated_on": "Generated on",
                "project_structure": "Project Structure",
                "file": "File",
                "class": "Class",
                "function": "Function",
                "variables": "Variables",
                "source_code": "Source Code",
                "explanation": "Explanation",
                "docstring": "Docstring",
                "location": "Location",
                "line": "Line",
                "no_explanation": "No explanation available",
                "decorator": "Interface Decorator"
            }
        }
        self.t = self.texts[language]
    
    def generate_markdown(
        self,
        project_name: str,
        file_structure: List[str],
        code_data: Dict,
        explanations: Dict[str, str]
    ) -> str:
        """
        生成 Markdown 文档
        
        Args:
            project_name: 项目名称
            file_structure: 文件结构列表
            code_data: 包含 classes, functions, variables 的字典
            explanations: 代码元素解释字典，key 为 "file::type::name"
        
        Returns:
            Markdown 格式的文档字符串
        """
        lines = []
        
        # 标题
        lines.append(f"# {self.t['title']}: {project_name}\n")
        lines.append(f"_{self.t['generated_on']}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
        lines.append("\n---\n")
        
        # 项目结构
        if file_structure:
            lines.append(f"## {self.t['project_structure']}\n")
            for file_path in file_structure:
                lines.append(f"- `{file_path}`")
            lines.append("\n---\n")
        
        # 按文件组织内容
        files_data = {}
        
        # 组织类
        classes_list = code_data.get("classes", [])
        if not classes_list:
            print("  ⚠️  Warning: No class data in code_data")
        for cls in classes_list:
            if not cls:
                continue
            file_name = cls[1] if isinstance(cls, tuple) and len(cls) > 1 else (cls.get("file", "unknown") if isinstance(cls, dict) else "unknown")
            if file_name not in files_data:
                files_data[file_name] = {"classes": [], "functions": [], "variables": []}
            files_data[file_name]["classes"].append(cls)
        
        # 组织函数
        functions_list = code_data.get("functions", [])
        if not functions_list:
            print("  ⚠️  Warning: No function data in code_data")
        for func in functions_list:
            if not func:
                continue
            file_name = func[1] if isinstance(func, tuple) and len(func) > 1 else (func.get("file", "unknown") if isinstance(func, dict) else "unknown")
            if file_name not in files_data:
                files_data[file_name] = {"classes": [], "functions": [], "variables": []}
            files_data[file_name]["functions"].append(func)
        
        # 组织变量
        for var in code_data.get("variables", []):
            file_name = var[1] if isinstance(var, tuple) else var.get("file", "unknown")
            if file_name not in files_data:
                files_data[file_name] = {"classes": [], "functions": [], "variables": []}
            files_data[file_name]["variables"].append(var)
        
        # 生成每个文件的文档
        for file_name in sorted(files_data.keys()):
            lines.append(f"## {self.t['file']}: `{file_name}`\n")
            
            file_data = files_data[file_name]
            
            # 类
            if file_data["classes"]:
                lines.append(f"### {self.t['class']}\n")
                for cls in file_data["classes"]:
                    if isinstance(cls, tuple):
                        name, file, start, end = cls[0], cls[1], cls[2], cls[3]
                        code_snippet = cls[4] if len(cls) > 4 else ""
                        docstring = cls[5] if len(cls) > 5 else None
                    else:
                        name = cls.get("name", "unknown")
                        file = cls.get("file", file_name)
                        start = cls.get("start_line", 0)
                        end = cls.get("end_line", 0)
                        code_snippet = cls.get("code", "")
                        docstring = cls.get("docstring")
                    
                    element_id = f"{file}::class::{name}"
                    explanation = explanations.get(element_id, self.t["no_explanation"])
                    
                    lines.append(f"#### `{name}`\n")
                    lines.append(f"- **{self.t['location']}**: {self.t['line']} {start}-{end}\n")
                    
                    if docstring:
                        lines.append(f"- **{self.t['docstring']}**: {docstring}\n")
                    
                    if code_snippet:
                        lines.append(f"\n**{self.t['source_code']}:**\n")
                        lines.append("```python")
                        lines.append(code_snippet)
                        lines.append("```\n")
                    
                    lines.append(f"\n**{self.t['explanation']}:**\n")
                    lines.append(f"{explanation}\n")
                    lines.append("\n---\n")
            
            # 函数
            if file_data["functions"]:
                lines.append(f"### {self.t['function']}\n")
                for func in file_data["functions"]:
                    if isinstance(func, tuple):
                        name, file, class_name, start, end = func[0], func[1], func[2], func[3], func[4]
                        code_snippet = func[5] if len(func) > 5 else ""
                        docstring = func[6] if len(func) > 6 else None
                        decorators = func[7] if len(func) > 7 else []
                    else:
                        name = func.get("name", "unknown")
                        file = func.get("file", file_name)
                        class_name = func.get("class_name", "")
                        start = func.get("start_line", 0)
                        end = func.get("end_line", 0)
                        code_snippet = func.get("code", "")
                        docstring = func.get("docstring")
                        decorators = func.get("decorators", [])
                    
                    element_id = f"{file}::function::{name}"
                    explanation = explanations.get(element_id, self.t["no_explanation"])
                    
                    func_title = f"`{name}`"
                    if class_name:
                        func_title += f" (in class `{class_name}`)"
                    lines.append(f"#### {func_title}\n")
                    lines.append(f"- **{self.t['location']}**: {self.t['line']} {start}-{end}\n")
                    
                    # 显示装饰器信息（接口路由等）
                    if decorators:
                        decorator_strs = []
                        for dec in decorators:
                            if isinstance(dec, dict):
                                dec_name = dec.get("name", "")
                                dec_args = dec.get("args", [])
                                if dec_args:
                                    dec_str = f"@{dec_name}({', '.join(dec_args)})"
                                else:
                                    dec_str = f"@{dec_name}"
                                decorator_strs.append(dec_str)
                        if decorator_strs:
                            lines.append(f"- **{self.t['decorator']}**: {', '.join(decorator_strs)}\n")
                    
                    if docstring:
                        lines.append(f"- **{self.t['docstring']}**: {docstring}\n")
                    
                    if code_snippet:
                        lines.append(f"\n**{self.t['source_code']}:**\n")
                        lines.append("```python")
                        lines.append(code_snippet)
                        lines.append("```\n")
                    
                    lines.append(f"\n**{self.t['explanation']}:**\n")
                    lines.append(f"{explanation}\n")
                    lines.append("\n---\n")
            
            # 变量（可选，通常不包含在详细文档中）
            # if file_data["variables"]:
            #     lines.append(f"### {self.t['variables']}\n")
            #     for var in file_data["variables"]:
            #         ...
        
        return "\n".join(lines)
    
    def save_markdown(self, markdown_text: str, output_path: str):
        """保存 Markdown 文件"""
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        print(f"✅ Markdown saved to {output_path}")
    
    def markdown_to_pdf(self, markdown_text: str, output_path: str):
        """
        将 Markdown 转换为 PDF
        
        Args:
            markdown_text: Markdown 文本
            output_path: PDF 输出路径
        """
        if not WEASYPRINT_AVAILABLE:
            error_msg = (
                "❌ WeasyPrint is not available. Cannot generate PDF.\n"
                "⚠️  To install WeasyPrint dependencies:\n"
                "   On macOS: brew install cairo pango gdk-pixbuf libffi\n"
                "   On Ubuntu: sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0\n"
                "   Then: pip install weasyprint"
            )
            print(error_msg)
            raise ImportError("WeasyPrint is not available")
        
        try:
            # 将 Markdown 转换为 HTML
            html_content = markdown(
                markdown_text,
                extensions=['codehilite', 'fenced_code', 'tables']
            )
            
            # 添加基本样式
            html_with_style = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: "Helvetica Neue", Arial, sans-serif;
                        line-height: 1.6;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    code {{
                        background-color: #f4f4f4;
                        padding: 2px 4px;
                        border-radius: 3px;
                        font-family: "Courier New", monospace;
                    }}
                    pre {{
                        background-color: #f4f4f4;
                        padding: 10px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                    pre code {{
                        background-color: transparent;
                        padding: 0;
                    }}
                    h1, h2, h3, h4 {{
                        color: #333;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f2f2f2;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # 使用 WeasyPrint 转换为 PDF
            HTML(string=html_with_style).write_pdf(output_path)
            print(f"✅ PDF saved to {output_path}")
            
        except Exception as e:
            error_msg = (
                f"❌ Error converting to PDF: {str(e)}\n"
                "⚠️  Make sure WeasyPrint dependencies are installed:\n"
                "   On macOS: brew install cairo pango gdk-pixbuf libffi\n"
                "   On Ubuntu: sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0\n"
                "   Then: pip install weasyprint"
            )
            print(error_msg)
            # 不抛出异常，让程序继续运行，至少 Markdown 已经生成了
            raise

