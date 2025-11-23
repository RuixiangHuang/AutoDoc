#!/usr/bin/env python3
"""
主流程控制器：整合所有模块，实现完整的文档生成流程
"""
import os
import argparse
import json
from main import scan_directory, extract_code_elements
from database import init_database, clear_database, save_classes, save_functions, save_variables
from vector_store import VectorStore
from langchain_query import LangChainQuery
from document_generator import DocumentGenerator
from langchain_community.llms import Ollama


def get_file_structure(directory: str) -> dict:
    """获取详细的目录结构"""
    structure = {
        "files": [],
        "directories": []
    }
    
    for root, dirs, files in os.walk(directory):
        # 获取相对路径
        rel_root = os.path.relpath(root, directory)
        if rel_root == ".":
            rel_root = ""
        
        # 添加目录信息
        for dir_name in dirs:
            dir_path = os.path.join(rel_root, dir_name) if rel_root else dir_name
            structure["directories"].append(dir_path)
        
        # 添加 Python 文件信息
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(rel_root, file) if rel_root else file
                full_path = os.path.join(root, file)
                # 获取文件大小（用于判断重要性）
                try:
                    file_size = os.path.getsize(full_path)
                except:
                    file_size = 0
                
                structure["files"].append({
                    "path": file_path,
                    "name": file,
                    "size": file_size,
                    "full_path": full_path
                })
    
    structure["files"].sort(key=lambda x: x["path"])
    structure["directories"].sort()
    return structure


def identify_interface_files(file_structure: dict, language: str = "zh") -> list:
    """
    使用 LLM 识别哪些文件是接口文件
    
    Args:
        file_structure: 目录结构字典
        language: 语言选择
    
    Returns:
        接口文件路径列表
    """
    llm = Ollama(model="qwen3-coder:30b")
    
    # Build directory structure description
    structure_text = "Directory structure:\n"
    structure_text += f"Directories: {', '.join(file_structure['directories'][:20])}\n"  # Limit display count
    structure_text += "\nPython file list:\n"
    for file_info in file_structure["files"][:50]:  # Limit to first 50 files
        structure_text += f"  - {file_info['path']} ({file_info['size']} bytes)\n"
    if len(file_structure["files"]) > 50:
        structure_text += f"  ... {len(file_structure['files']) - 50} more files\n"
    
    # 构建提示词
    if language == "zh":
        prompt = f"""请分析以下项目目录结构，识别出哪些文件是接口文件（如 controller、API、路由、端点等）。

{structure_text}

请只返回接口文件的路径列表，每行一个路径，格式如下：
文件路径1
文件路径2
文件路径3

只返回路径，不要添加任何解释或其他文字。如果某个文件明显是接口文件（如包含 controller、api、route、endpoint、handler 等关键词），请包含它。"""
    else:
        prompt = f"""Please analyze the following project directory structure and identify which files are interface files (such as controllers, APIs, routes, endpoints, etc.).

{structure_text}

Please return only a list of interface file paths, one path per line, in the following format:
file_path1
file_path2
file_path3

Return only the paths, without any explanations or other text. If a file is clearly an interface file (e.g., contains keywords like controller, api, route, endpoint, handler), please include it."""
    
    try:
        response = llm.invoke(prompt)
        
        # 解析响应，提取文件路径
        interface_files = []
        for line in response.strip().split('\n'):
            line = line.strip()
            # 移除可能的编号、符号等
            line = line.lstrip('0123456789.-) ').strip()
            if line and not line.startswith('#'):
                # 检查这个路径是否在文件列表中
                for file_info in file_structure["files"]:
                    if line in file_info["path"] or file_info["path"].endswith(line):
                        interface_files.append(file_info["path"])
                        break
        
        return list(set(interface_files))  # 去重
        
    except Exception as e:
        print(f"  ⚠️  Error identifying interface files with LLM: {str(e)}")
        print("  Will use default keyword filtering (controller, api, route, etc.)")
        # Fallback to keyword filtering
        keywords = ['controller', 'api', 'route', 'endpoint', 'handler', 'service']
        interface_files = []
        for file_info in file_structure["files"]:
            file_lower = file_info["path"].lower()
            if any(keyword in file_lower for keyword in keywords):
                interface_files.append(file_info["path"])
        return interface_files


def prepare_code_elements_for_vector_store(classes, functions, file_paths_map):
    """准备代码元素用于向量数据库存储"""
    code_elements = []
    
    # 处理类
    for cls in classes:
        name, file, start, end, code_snippet, docstring = cls
        full_path = file_paths_map.get(file, file)
        
        # 构建用于向量化的文本（包含代码和元数据）
        text = f"class {name}\n{code_snippet}"
        if docstring:
            text = f"{docstring}\n{text}"
        
        code_elements.append({
            "text": text,
            "metadata": {
                "type": "class",
                "name": name,
                "file": file,
                "start_line": start,
                "end_line": end,
                "class_name": "",
                "docstring": docstring or ""
            }
        })
    
    # 处理函数
    for func in functions:
        # 函数元组可能是 7 个或 8 个元素（新版本包含 decorators）
        if len(func) >= 7:
            name, file, class_name, start, end, code_snippet, docstring = func[0:7]
            decorators = func[7] if len(func) > 7 else []
        else:
            name, file, class_name, start, end, code_snippet, docstring = func
            decorators = []
        
        full_path = file_paths_map.get(file, file)
        
        # 构建用于向量化的文本
        text = f"def {name}\n{code_snippet}"
        if docstring:
            text = f"{docstring}\n{text}"
        
        # 添加装饰器信息
        decorator_info = []
        for dec in decorators:
            if isinstance(dec, dict):
                dec_str = dec.get("name", "")
                if dec.get("args"):
                    dec_str += f"({', '.join(dec['args'])})"
                decorator_info.append(dec_str)
        
        code_elements.append({
            "text": text,
            "metadata": {
                "type": "function",
                "name": name,
                "file": file,
                "start_line": start,
                "end_line": end,
                "class_name": class_name or "",
                "docstring": docstring or "",
                "decorators": ", ".join(decorator_info) if decorator_info else ""
            }
        })
    
    return code_elements


def prepare_code_elements_for_explanation(classes, functions):
    """准备代码元素用于 LLM 解释"""
    elements = []
    
    # 处理类
    for cls in classes:
        name, file, start, end, code_snippet, docstring = cls
        elements.append({
            "name": name,
            "type": "class",
            "file": file,
            "code": code_snippet
        })
    
    # 处理函数
    for func in functions:
        # 函数元组可能是 7 个或 8 个元素
        if len(func) >= 7:
            name, file, class_name, start, end, code_snippet, docstring = func[0:7]
        else:
            name, file, class_name, start, end, code_snippet, docstring = func
        elements.append({
            "name": name,
            "type": "function",
            "file": file,
            "code": code_snippet,
            "class_name": class_name
        })
    
    return elements


def progress_callback(current: int, total: int):
    """Progress callback function"""
    percentage = (current / total) * 100
    print(f"Progress: {current}/{total} ({percentage:.1f}%)")


def generate_documentation(
    code_directory: str,
    output_dir: str = "output",
    language: str = "en",
    file_filter_keywords: str = "controller,api,route,endpoint,handler,service"
):
    """
    Main function to generate complete documentation
    
    Args:
        code_directory: Code directory to analyze
        output_dir: Output directory
        language: Language selection, "zh" or "en"
    """
    print("=" * 60)
    print("AutoDoc - Code Documentation Generation System")
    print("=" * 60)
    print(f"Code Directory: {code_directory}")
    print(f"Output Directory: {output_dir}")
    print(f"Language: {'Chinese' if language == 'zh' else 'English'}")
    print("=" * 60)
    
    # Step 1: Initialize database
    print("\n[1/6] Initializing database...")
    init_database()
    clear_database()
    
    # Step 2: Scan directory and analyze code
    print("\n[2/6] Scanning directory and analyzing code...")
    
    # File filter function: only scan files containing specified keywords
    def interface_file_filter(file_path, file_name):
        """Filter interface-related files"""
        keywords = [k.strip() for k in file_filter_keywords.split(',')]
        file_lower = file_name.lower()
        path_lower = file_path.lower()
        return any(keyword in file_lower or keyword in path_lower for keyword in keywords)
    
    classes, functions, variables = scan_directory(code_directory, file_filter=interface_file_filter)
    
    # 保存到数据库（只保存基本信息）
    classes_for_db = [(c[0], c[1], c[2], c[3]) for c in classes]
    # 函数元组可能是 7 个或 8 个元素，只取前 5 个用于数据库
    functions_for_db = [(f[0], f[1], f[2], f[3], f[4]) for f in functions]
    
    save_classes(classes_for_db)
    save_functions(functions_for_db)
    save_variables(variables)
    
    print(f"✅ Analysis completed: {len(classes)} classes, {len(functions)} functions, {len(variables)} variables")
    
    # Step 3: Get file structure (for document generation)
    print("\n[3/6] Getting file structure...")
    file_structure = get_file_structure(code_directory)
    
    # Build file path mapping (from filename to full path)
    # Note: The file field in CodeAnalyzer is the filename (os.path.basename), so use name as key
    file_paths_map = {}
    for file_info in file_structure["files"]:
        file_name = file_info["name"]  # Filename, e.g., "example.py"
        file_paths_map[file_name] = file_info["full_path"]
    
    # Step 4: Store to vector database
    print("\n[4/6] Storing code to vector database...")
    print("  Initializing embedding model (first use will download model, may take a few minutes)...")
    vector_store = VectorStore()
    print("  Clearing vector database...")
    vector_store.clear()
    
    print(f"  Preparing {len(classes)} classes and {len(functions)} functions for code elements...")
    code_elements = prepare_code_elements_for_vector_store(classes, functions, file_paths_map)
    print(f"  Generating embeddings and storing to vector database ({len(code_elements)} elements, may take some time)...")
    vector_store.add_code_elements(code_elements)
    
    # Step 5: Generate explanations using LLM (process one by one)
    print("\n[5/6] Generating code explanations using LLM (processing one by one)...")
    langchain_query = LangChainQuery(vector_store, language=language)
    
    elements_for_explanation = prepare_code_elements_for_explanation(classes, functions)
    explanations = langchain_query.batch_explain(
        elements_for_explanation,
        progress_callback=progress_callback
    )
    
    print(f"✅ Generated explanations for {len(explanations)} code elements")
    
    # Step 6: Generate documentation
    print("\n[6/6] Generating Markdown documentation...")
    doc_generator = DocumentGenerator(language=language)
    
    project_name = os.path.basename(os.path.abspath(code_directory))
    
    # 准备文件结构列表（用于文档显示）
    file_structure_list = [f["path"] for f in file_structure["files"]]
    
    code_data = {
        "classes": classes,
        "functions": functions,
        "variables": variables
    }
    
    # Debug information
    print(f"  Preparing to generate documentation: {len(classes)} classes, {len(functions)} functions, {len(variables)} variables")
    if len(classes) == 0 and len(functions) == 0:
        print("  ⚠️  Warning: No classes or functions found!")
        print("  Possible reasons:")
        print("    1. No Python files in the project directory")
        print("    2. Python files are empty or only contain comments")
        print("    3. All functions were filtered out (e.g., all are __init__ and other magic methods)")
    
    markdown_text = doc_generator.generate_markdown(
        project_name=project_name,
        file_structure=file_structure_list,
        code_data=code_data,
        explanations=explanations
    )
    
    # 保存 Markdown
    os.makedirs(output_dir, exist_ok=True)
    md_output_path = os.path.join(output_dir, f"documentation_{language}.md")
    doc_generator.save_markdown(markdown_text, md_output_path)
    
    print("\n" + "=" * 60)
    print("✅ Documentation generation completed!")
    print(f"   Markdown: {md_output_path}")
    print("=" * 60)


def main():
    """Command line entry point"""
    parser = argparse.ArgumentParser(
        description="AutoDoc - Code Documentation Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python doc_generator.py code/                    # Analyze code/ directory, generate English documentation
  python doc_generator.py code/ --lang zh          # Generate Chinese documentation
  python doc_generator.py code/ --output docs/    # Specify output directory
  python doc_generator.py code/ --filter controller,api  # Only scan files containing controller or api
        """
    )
    
    parser.add_argument(
        "directory",
        type=str,
        help="Path to the code directory to analyze"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        "--lang", "-l",
        type=str,
        choices=["zh", "en"],
        default="en",
        help="Documentation language: zh (Chinese) or en (English) (default: en)"
    )
    
    parser.add_argument(
        "--filter",
        type=str,
        default="controller,api,route,endpoint,handler,service",
        help="File filter keywords (comma-separated), only scan files containing these keywords (default: controller,api,route,endpoint,handler,service)"
    )
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.isdir(args.directory):
        print(f"❌ Error: Directory '{args.directory}' does not exist")
        return 1
    
    try:
        generate_documentation(
            code_directory=args.directory,
            output_dir=args.output,
            language=args.lang,
            file_filter_keywords=args.filter
        )
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  User interrupted")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

