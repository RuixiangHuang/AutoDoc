#!/usr/bin/env python3
"""
主流程控制器：整合所有模块，实现完整的文档生成流程
"""
import os
import argparse
from main import scan_directory, extract_code_elements
from database import init_database, clear_database, save_classes, save_functions, save_variables
from vector_store import VectorStore
from langchain_query import LangChainQuery
from document_generator import DocumentGenerator


def get_file_structure(directory: str) -> list:
    """获取文件结构列表"""
    file_list = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file), directory)
                file_list.append(rel_path)
    return sorted(file_list)


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
        name, file, class_name, start, end, code_snippet, docstring = func
        full_path = file_paths_map.get(file, file)
        
        # 构建用于向量化的文本
        text = f"def {name}\n{code_snippet}"
        if docstring:
            text = f"{docstring}\n{text}"
        
        code_elements.append({
            "text": text,
            "metadata": {
                "type": "function",
                "name": name,
                "file": file,
                "start_line": start,
                "end_line": end,
                "class_name": class_name or "",
                "docstring": docstring or ""
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
    generate_pdf: bool = True
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
    classes, functions, variables = scan_directory(code_directory)
    
    # 保存到数据库（只保存基本信息）
    classes_for_db = [(c[0], c[1], c[2], c[3]) for c in classes]
    functions_for_db = [(f[0], f[1], f[2], f[3], f[4]) for f in functions]
    
    save_classes(classes_for_db)
    save_functions(functions_for_db)
    save_variables(variables)
    
    print(f"✅ 分析完成: {len(classes)} 个类, {len(functions)} 个函数, {len(variables)} 个变量")
    
    # 步骤 3: 准备文件路径映射
    file_paths_map = {}
    for root, _, files in os.walk(code_directory):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                file_paths_map[os.path.basename(file)] = full_path
    
    # 步骤 4: 存储到向量数据库
    print("\n[3/6] 存储代码到向量数据库...")
    vector_store = VectorStore()
    vector_store.clear()
    
    code_elements = prepare_code_elements_for_vector_store(classes, functions, file_paths_map)
    vector_store.add_code_elements(code_elements)
    
    # 步骤 5: 使用 LLM 生成解释（逐个处理）
    print("\n[4/6] 使用 LLM 生成代码解释（逐个处理）...")
    langchain_query = LangChainQuery(vector_store, language=language)
    
    elements_for_explanation = prepare_code_elements_for_explanation(classes, functions)
    explanations = langchain_query.batch_explain(
        elements_for_explanation,
        progress_callback=progress_callback
    )
    
    print(f"✅ 生成了 {len(explanations)} 个代码元素的解释")
    
    # 步骤 6: 生成文档
    print("\n[5/6] 生成 Markdown 文档...")
    doc_generator = DocumentGenerator(language=language)
    
    file_structure = get_file_structure(code_directory)
    project_name = os.path.basename(os.path.abspath(code_directory))
    
    code_data = {
        "classes": classes,
        "functions": functions,
        "variables": variables
    }
    
    markdown_text = doc_generator.generate_markdown(
        project_name=project_name,
        file_structure=file_structure,
        code_data=code_data,
        explanations=explanations
    )
    
    # 保存 Markdown
    os.makedirs(output_dir, exist_ok=True)
    md_output_path = os.path.join(output_dir, f"documentation_{language}.md")
    doc_generator.save_markdown(markdown_text, md_output_path)
    
    # 步骤 7: 转换为 PDF（如果启用）
    if generate_pdf:
        print("\n[6/6] 转换为 PDF...")
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
            generate_pdf=not args.no_pdf
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

