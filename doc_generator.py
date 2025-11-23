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
    llm = Ollama(model="gemma3:12b")
    
    # 构建目录结构描述
    structure_text = "目录结构:\n"
    structure_text += f"目录: {', '.join(file_structure['directories'][:20])}\n"  # 限制显示数量
    structure_text += "\nPython 文件列表:\n"
    for file_info in file_structure["files"][:50]:  # 限制显示前50个文件
        structure_text += f"  - {file_info['path']} ({file_info['size']} bytes)\n"
    if len(file_structure["files"]) > 50:
        structure_text += f"  ... 还有 {len(file_structure['files']) - 50} 个文件\n"
    
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
        print(f"  ⚠️  LLM 识别接口文件时出错: {str(e)}")
        print("  将使用默认关键词过滤（controller, api, route 等）")
        # 回退到关键词过滤
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
    """进度回调函数"""
    percentage = (current / total) * 100
    print(f"处理进度: {current}/{total} ({percentage:.1f}%)")


def generate_documentation(
    code_directory: str,
    output_dir: str = "output",
    language: str = "zh",
    generate_pdf: bool = True,
    file_filter_keywords: str = "controller,api,route,endpoint,handler,service"
):
    """
    生成完整文档的主函数
    
    Args:
        code_directory: 要分析的代码目录
        output_dir: 输出目录
        language: 语言选择，"zh" 或 "en"
        generate_pdf: 是否生成 PDF
    """
    print("=" * 60)
    print("AutoDoc - 代码文档自动生成系统")
    print("=" * 60)
    print(f"代码目录: {code_directory}")
    print(f"输出目录: {output_dir}")
    print(f"语言: {'中文' if language == 'zh' else 'English'}")
    print("=" * 60)
    
    # 步骤 1: 初始化数据库
    print("\n[1/6] 初始化数据库...")
    init_database()
    clear_database()
    
    # 步骤 2: 扫描目录并分析代码
    print("\n[2/6] 扫描目录并分析代码...")
    
    # 文件过滤函数：只扫描包含指定关键词的文件
    def interface_file_filter(file_path, file_name):
        """过滤接口相关文件"""
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
    
    print(f"✅ 分析完成: {len(classes)} 个类, {len(functions)} 个函数, {len(variables)} 个变量")
    
    # 步骤 4: 存储到向量数据库
    print("\n[4/6] 存储代码到向量数据库...")
    print("  正在初始化嵌入模型（首次使用会下载模型，可能需要几分钟）...")
    vector_store = VectorStore()
    print("  清空向量数据库...")
    vector_store.clear()
    
    print(f"  准备 {len(classes)} 个类和 {len(functions)} 个函数的代码元素...")
    code_elements = prepare_code_elements_for_vector_store(classes, functions, file_paths_map)
    print(f"  正在生成嵌入向量并存储到向量数据库（共 {len(code_elements)} 个元素，可能需要一些时间）...")
    vector_store.add_code_elements(code_elements)
    
    # 步骤 5: 使用 LLM 生成解释（逐个处理）
    print("\n[5/6] 使用 LLM 生成代码解释（逐个处理）...")
    langchain_query = LangChainQuery(vector_store, language=language)
    
    elements_for_explanation = prepare_code_elements_for_explanation(classes, functions)
    explanations = langchain_query.batch_explain(
        elements_for_explanation,
        progress_callback=progress_callback
    )
    
    print(f"✅ 生成了 {len(explanations)} 个代码元素的解释")
    
    # 步骤 6: 生成文档
    print("\n[6/6] 生成 Markdown 文档...")
    doc_generator = DocumentGenerator(language=language)
    
    project_name = os.path.basename(os.path.abspath(code_directory))
    
    # 准备文件结构列表（用于文档显示）
    file_structure_list = [f["path"] for f in file_structure["files"]]
    
    code_data = {
        "classes": classes,
        "functions": functions,
        "variables": variables
    }
    
    # 调试信息
    print(f"  准备生成文档: {len(classes)} 个类, {len(functions)} 个函数, {len(variables)} 个变量")
    if len(classes) == 0 and len(functions) == 0:
        print("  ⚠️  警告: 没有找到任何类或函数！")
        print("  可能的原因:")
        print("    1. 项目目录中没有 Python 文件")
        print("    2. Python 文件都是空的或只包含注释")
        print("    3. 所有函数都被过滤掉了（如都是 __init__ 等魔法方法）")
    
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
    
    # 步骤 7: 转换为 PDF（如果启用）
    if generate_pdf:
        print("\n[7/7] 转换为 PDF...")
        pdf_output_path = os.path.join(output_dir, f"documentation_{language}.pdf")
        try:
            doc_generator.markdown_to_pdf(markdown_text, pdf_output_path)
        except Exception as e:
            print(f"⚠️  PDF 生成失败: {str(e)}")
            print("   但 Markdown 文件已成功生成")
    
    print("\n" + "=" * 60)
    print("✅ 文档生成完成！")
    print(f"   Markdown: {md_output_path}")
    if generate_pdf:
        print(f"   PDF: {pdf_output_path}")
    print("=" * 60)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="AutoDoc - 代码文档自动生成系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python doc_generator.py code/                    # 分析 code/ 目录，生成中文文档
  python doc_generator.py code/ --lang en          # 生成英文文档
  python doc_generator.py code/ --no-pdf            # 只生成 Markdown，不生成 PDF
  python doc_generator.py code/ --output docs/      # 指定输出目录
  python doc_generator.py code/ --filter controller,api  # 只扫描包含 controller 或 api 的文件
        """
    )
    
    parser.add_argument(
        "directory",
        type=str,
        help="要分析的代码目录路径"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="输出目录（默认: output）"
    )
    
    parser.add_argument(
        "--lang", "-l",
        type=str,
        choices=["zh", "en"],
        default="zh",
        help="文档语言: zh (中文) 或 en (英文) (默认: zh)"
    )
    
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="不生成 PDF，只生成 Markdown"
    )
    
    parser.add_argument(
        "--filter",
        type=str,
        default="controller,api,route,endpoint,handler,service",
        help="文件过滤关键词（逗号分隔），只扫描包含这些关键词的文件（默认: controller,api,route,endpoint,handler,service）"
    )
    
    args = parser.parse_args()
    
    # 检查目录是否存在
    if not os.path.isdir(args.directory):
        print(f"❌ 错误: 目录 '{args.directory}' 不存在")
        return 1
    
    try:
        generate_documentation(
            code_directory=args.directory,
            output_dir=args.output,
            language=args.lang,
            generate_pdf=not args.no_pdf,
            file_filter_keywords=args.filter
        )
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

