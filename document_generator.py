import os
from datetime import datetime
from typing import Dict, List, Optional
from elements import element_id

if os.path.exists("/opt/homebrew/lib"):
    os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")
    if "DYLD_LIBRARY_PATH" in os.environ and "/opt/homebrew/lib" not in os.environ["DYLD_LIBRARY_PATH"]:
        os.environ["DYLD_LIBRARY_PATH"] = f"/opt/homebrew/lib:{os.environ['DYLD_LIBRARY_PATH']}"

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError, Exception) as e:
    WEASYPRINT_AVAILABLE = False
    HTML = None


class DocumentGenerator:
    """Generate Markdown and PDF documentation"""
    
    def __init__(self):
        self.texts = {
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
    
    def generate_markdown(
        self,
        project_name: str,
        file_structure: List[str],
        code_data: Dict,
        explanations: Dict[str, str]
    ) -> str:
        lines = []
        
        lines.append(f"# {self.texts['title']}: {project_name}\n")
        lines.append(f"_{self.texts['generated_on']}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
        lines.append("\n---\n")
        
        if file_structure:
            lines.append(f"## {self.texts['project_structure']}\n")
            for file_path in file_structure:
                lines.append(f"- `{file_path}`")
            lines.append("\n---\n")
        
        files_data = {}
        
        classes_list = code_data.get("classes", [])
        if not classes_list:
            print("  Warning: No class data in code_data")
        for cls in classes_list:
            if not cls:
                continue
            file_name = cls[1] if isinstance(cls, tuple) and len(cls) > 1 else (cls.get("file", "unknown") if isinstance(cls, dict) else "unknown")
            if file_name not in files_data:
                files_data[file_name] = {"classes": [], "functions": [], "variables": []}
            files_data[file_name]["classes"].append(cls)
        
        functions_list = code_data.get("functions", [])
        if not functions_list:
            print("  Warning: No function data in code_data")
        for func in functions_list:
            if not func:
                continue
            file_name = func[1] if isinstance(func, tuple) and len(func) > 1 else (func.get("file", "unknown") if isinstance(func, dict) else "unknown")
            if file_name not in files_data:
                files_data[file_name] = {"classes": [], "functions": [], "variables": []}
            files_data[file_name]["functions"].append(func)
        
        for var in code_data.get("variables", []):
            file_name = var[1] if isinstance(var, tuple) else var.get("file", "unknown")
            if file_name not in files_data:
                files_data[file_name] = {"classes": [], "functions": [], "variables": []}
            files_data[file_name]["variables"].append(var)
        
        for file_name in sorted(files_data.keys()):
            lines.append(f"## {self.texts['file']}: `{file_name}`\n")
            
            file_data = files_data[file_name]
            
            if file_data["classes"]:
                lines.append(f"### {self.texts['class']}\n")
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
                    
                    explanation = explanations.get(element_id(file, "class", name), self.texts["no_explanation"])
                    
                    lines.append(f"#### `{name}`\n")
                    lines.append(f"- **{self.texts['location']}**: {self.texts['line']} {start}-{end}\n")
                    
                    if docstring:
                        lines.append(f"- **{self.texts['docstring']}**: {docstring}\n")
                    
                    if code_snippet:
                        lines.append(f"\n**{self.texts['source_code']}:**\n")
                        lines.append("```python")
                        lines.append(code_snippet)
                        lines.append("```\n")
                    
                    lines.append(f"\n**{self.texts['explanation']}:**\n")
                    lines.append(f"{explanation}\n")
                    lines.append("\n---\n")
            
            if file_data["functions"]:
                lines.append(f"### {self.texts['function']}\n")
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
                    
                    explanation = explanations.get(element_id(file, "function", name, class_name), self.texts["no_explanation"])
                    
                    func_title = f"`{name}`"
                    if class_name:
                        func_title += f" (in class `{class_name}`)"
                    lines.append(f"#### {func_title}\n")
                    lines.append(f"- **{self.texts['location']}**: {self.texts['line']} {start}-{end}\n")
                    
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
                            lines.append(f"- **{self.texts['decorator']}**: {', '.join(decorator_strs)}\n")
                    
                    if docstring:
                        lines.append(f"- **{self.texts['docstring']}**: {docstring}\n")
                    
                    if code_snippet:
                        lines.append(f"\n**{self.texts['source_code']}:**\n")
                        lines.append("```python")
                        lines.append(code_snippet)
                        lines.append("```\n")
                    
                    lines.append(f"\n**{self.texts['explanation']}:**\n")
                    lines.append(f"{explanation}\n")
                    lines.append("\n---\n")
        
        return "\n".join(lines)
    
    def save_markdown(self, markdown_text: str, output_path: str):
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        print(f"Markdown saved to {output_path}")
    
    def markdown_to_pdf(self, markdown_text: str, output_path: str):
        if not WEASYPRINT_AVAILABLE:
            error_msg = (
                "WeasyPrint is not available. Cannot generate PDF.\n"
                "To install WeasyPrint dependencies:\n"
                "   On macOS: brew install cairo pango gdk-pixbuf libffi\n"
                "   On Ubuntu: sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0\n"
                "   Then: pip install weasyprint"
            )
            print(error_msg)
            raise ImportError("WeasyPrint is not available")
        
        from markdown import markdown

        try:
            html_content = markdown(
                markdown_text,
                extensions=['codehilite', 'fenced_code', 'tables']
            )
            
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
            
            HTML(string=html_with_style).write_pdf(output_path)
            print(f"PDF saved to {output_path}")
            
        except Exception as e:
            error_msg = (
                f"Error converting to PDF: {str(e)}\n"
                "Make sure WeasyPrint dependencies are installed:\n"
                "   On macOS: brew install cairo pango gdk-pixbuf libffi\n"
                "   On Ubuntu: sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0\n"
                "   Then: pip install weasyprint"
            )
            print(error_msg)
            raise

