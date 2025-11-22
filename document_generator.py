import os
from datetime import datetime
from typing import Dict, List, Optional
from weasyprint import HTML
from markdown import markdown


class DocumentGenerator:
    """生成 Markdown 和 PDF 文档"""
    
    def __init__(self, language: str = "zh"):
        """
        初始化文档生成器
        
        Args:
            language: 语言选择，"zh" 为中文，"en" 为英文
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
                "no_explanation": "暂无说明"
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
                "no_explanation": "No explanation available"
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
        for cls in code_data.get("classes", []):
            file_name = cls[1] if isinstance(cls, tuple) else cls.get("file", "unknown")
            if file_name not in files_data:
                files_data[file_name] = {"classes": [], "functions": [], "variables": []}
            files_data[file_name]["classes"].append(cls)
        
        # 组织函数
        for func in code_data.get("functions", []):
            file_name = func[1] if isinstance(func, tuple) else func.get("file", "unknown")
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
                    else:
                        name = func.get("name", "unknown")
                        file = func.get("file", file_name)
                        class_name = func.get("class_name", "")
                        start = func.get("start_line", 0)
                        end = func.get("end_line", 0)
                        code_snippet = func.get("code", "")
                        docstring = func.get("docstring")
                    
                    element_id = f"{file}::function::{name}"
                    explanation = explanations.get(element_id, self.t["no_explanation"])
                    
                    func_title = f"`{name}`"
                    if class_name:
                        func_title += f" (in class `{class_name}`)"
                    lines.append(f"#### {func_title}\n")
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
            print(f"❌ Error converting to PDF: {str(e)}")
            print("⚠️  Make sure WeasyPrint dependencies are installed:")
            print("   On macOS: brew install cairo pango gdk-pixbuf libffi")
            print("   On Ubuntu: sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0")
            raise

