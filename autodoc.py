#!/usr/bin/env python3
"""
Main process controller: Integrate all modules to implement complete documentation generation workflow
"""
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
import json
from main import scan_directory, extract_code_elements
from database import init_database, clear_database, save_classes, save_functions, save_variables
from vector_store import VectorStore
from langchain_query import LangChainQuery
from document_generator import DocumentGenerator
from langchain_community.llms import Ollama
from config import get_config, LLMConfig

try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    ChatGroq = None


def get_file_structure(directory: str) -> dict:
    """Get detailed directory structure"""
    structure = {
        "files": [],
        "directories": []
    }
    
    for root, dirs, files in os.walk(directory):
        # Get relative path
        rel_root = os.path.relpath(root, directory)
        if rel_root == ".":
            rel_root = ""
        
        # Add directory information
        for dir_name in dirs:
            dir_path = os.path.join(rel_root, dir_name) if rel_root else dir_name
            structure["directories"].append(dir_path)
        
        # Add Python file information
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(rel_root, file) if rel_root else file
                full_path = os.path.join(root, file)
                # Get file size (for determining importance)
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


def identify_interface_files(file_structure: dict) -> list:
    config = get_config()
    provider = config.get_provider()
    
    if provider == LLMConfig.PROVIDER_GROQ:
        if not GROQ_AVAILABLE:
            print("  langchain-groq is not installed, using keyword filtering")
            keywords = ['controller', 'api', 'route', 'endpoint', 'handler', 'service']
            interface_files = []
            for file_info in file_structure["files"]:
                file_lower = file_info["path"].lower()
                if any(keyword in file_lower for keyword in keywords):
                    interface_files.append(file_info["path"])
            return interface_files
        
        api_key = config.get_groq_api_key()
        if not api_key:
            print("  Groq API Key is not set, using keyword filtering")
            keywords = ['controller', 'api', 'route', 'endpoint', 'handler', 'service']
            interface_files = []
            for file_info in file_structure["files"]:
                file_lower = file_info["path"].lower()
                if any(keyword in file_lower for keyword in keywords):
                    interface_files.append(file_info["path"])
            return interface_files
        
        llm = ChatGroq(
            groq_api_key=api_key,
            model_name=config.groq_model,
            temperature=0.1
        )
    else:
        llm = Ollama(model=config.ollama_model, base_url=config.ollama_base_url)
    
    structure_text = "Directory structure:\n"
    structure_text += f"Directories: {', '.join(file_structure['directories'][:20])}\n"
    structure_text += "\nPython file list:\n"
    for file_info in file_structure["files"][:50]:
        structure_text += f"  - {file_info['path']} ({file_info['size']} bytes)\n"
    if len(file_structure["files"]) > 50:
        structure_text += f"  ... {len(file_structure['files']) - 50} more files\n"
    
    prompt = f"""Please analyze the following project directory structure and identify which files are interface files (such as controllers, APIs, routes, endpoints, etc.).

{structure_text}

Please return only a list of interface file paths, one path per line, in the following format:
file_path1
file_path2
file_path3

Return only the paths, without any explanations or other text. If a file is clearly an interface file (e.g., contains keywords like controller, api, route, endpoint, handler), please include it."""
    
    try:
        response = llm.invoke(prompt)
        
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)
        
        interface_files = []
        for line in response_text.strip().split('\n'):
            line = line.strip()
            line = line.lstrip('0123456789.-) ').strip()
            if line and not line.startswith('#'):
                for file_info in file_structure["files"]:
                    if line in file_info["path"] or file_info["path"].endswith(line):
                        interface_files.append(file_info["path"])
                        break
        
        return list(set(interface_files))
        
    except Exception as e:
        print(f"  Error identifying interface files with LLM: {str(e)}")
        print("  Will use default keyword filtering (controller, api, route, etc.)")
        keywords = ['controller', 'api', 'route', 'endpoint', 'handler', 'service']
        interface_files = []
        for file_info in file_structure["files"]:
            file_lower = file_info["path"].lower()
            if any(keyword in file_lower for keyword in keywords):
                interface_files.append(file_info["path"])
        return interface_files


def prepare_code_elements_for_vector_store(classes, functions, file_paths_map):
    """Prepare code elements for vector database storage"""
    code_elements = []
    
    # Process classes
    for cls in classes:
        name, file, start, end, code_snippet, docstring = cls
        full_path = file_paths_map.get(file, file)
        
        # Build text for vectorization (including code and metadata)
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
    
    # Process functions
    for func in functions:
        # Function tuple may have 7 or 8 elements (new version includes decorators)
        if len(func) >= 7:
            name, file, class_name, start, end, code_snippet, docstring = func[0:7]
            decorators = func[7] if len(func) > 7 else []
        else:
            name, file, class_name, start, end, code_snippet, docstring = func
            decorators = []
        
        full_path = file_paths_map.get(file, file)
        
        # Build text for vectorization
        text = f"def {name}\n{code_snippet}"
        if docstring:
            text = f"{docstring}\n{text}"
        
        # Add decorator information
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
    """Prepare code elements for LLM explanation"""
    elements = []
    
    # Process classes
    for cls in classes:
        name, file, start, end, code_snippet, docstring = cls
        elements.append({
            "name": name,
            "type": "class",
            "file": file,
            "code": code_snippet
        })
    
    # Process functions
    for func in functions:
        # Function tuple may have 7 or 8 elements
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




def generate_documentation(
    code_directory: str,
    output_dir: str = "output",
    file_filter_keywords: str = "controller,api,route,endpoint,handler,service"
):
    print("=" * 60)
    print("AutoDoc - Code Documentation Generation System")
    print("=" * 60)
    
    # Check if input is a file or directory
    is_single_file = os.path.isfile(code_directory) and code_directory.endswith('.py')
    
    if is_single_file:
        print(f"Single File Mode: {code_directory}")
        print(f"Output Directory: {output_dir}")
    else:
        print(f"Code Directory: {code_directory}")
        print(f"Output Directory: {output_dir}")
    print("=" * 60)
    
    print("\n[1/6] Initializing database...")
    init_database()
    clear_database()
    
    print("\n[2/6] Scanning directory and analyzing code...")
    
    # Handle single file or directory
    if is_single_file:
        # Single file mode - analyze just this file
        print(f"Analyzing single file: {os.path.basename(code_directory)}")
        classes, functions, variables = extract_code_elements(code_directory)
        code_directory_for_structure = os.path.dirname(code_directory)
    else:
        # Directory mode - use filtering
        code_directory_for_structure = code_directory
        
        # If filter keywords are provided, use the filter
        if file_filter_keywords and file_filter_keywords.strip():
            def interface_file_filter(file_path, file_name):
                keywords = [k.strip() for k in file_filter_keywords.split(',') if k.strip()]
                if not keywords:  # If no valid keywords, don't filter
                    return True
                file_lower = file_name.lower()
                path_lower = file_path.lower()
                return any(keyword in file_lower or keyword in path_lower for keyword in keywords)
            
            classes, functions, variables = scan_directory(code_directory, file_filter=interface_file_filter)
        else:
            # Don't use filter, scan all files
            classes, functions, variables = scan_directory(code_directory, file_filter=None)
    
    classes_for_db = [(c[0], c[1], c[2], c[3]) for c in classes]
    functions_for_db = [(f[0], f[1], f[2], f[3], f[4]) for f in functions]
    
    save_classes(classes_for_db)
    save_functions(functions_for_db)
    save_variables(variables)
    
    print(f"Analysis completed: {len(classes)} classes, {len(functions)} functions, {len(variables)} variables")
    
    print("\n[3/6] Getting file structure...")
    if is_single_file:
        # Create minimal file structure for single file
        file_structure = {
            "files": [{
                "path": os.path.basename(code_directory),
                "name": os.path.basename(code_directory),
                "size": os.path.getsize(code_directory),
                "full_path": code_directory
            }],
            "directories": []
        }
    else:
        file_structure = get_file_structure(code_directory)
    
    file_paths_map = {}
    for file_info in file_structure["files"]:
        file_name = file_info["name"]
        file_paths_map[file_name] = file_info["full_path"]
    
    print("\n[4/6] Storing code to vector database...")
    print("  Initializing embedding model (first use will download model, may take a few minutes)...")
    vector_store = VectorStore()
    print("  Clearing vector database...")
    vector_store.clear()
    
    print(f"  Preparing {len(classes)} classes and {len(functions)} functions for code elements...")
    code_elements = prepare_code_elements_for_vector_store(classes, functions, file_paths_map)
    print(f"  Generating embeddings and storing to vector database ({len(code_elements)} elements, may take some time)...")
    vector_store.add_code_elements(code_elements)
    
    print("\n[5/6] Generating code explanations using LLM...")
    langchain_query = LangChainQuery(vector_store)
    
    elements_for_explanation = prepare_code_elements_for_explanation(classes, functions)
    explanations = langchain_query.batch_explain(elements_for_explanation)
    
    print(f"Generated explanations for {len(explanations)} code elements")
    
    print("\n[6/6] Generating Markdown documentation...")
    doc_generator = DocumentGenerator()
    
    if is_single_file:
        project_name = os.path.basename(code_directory).replace('.py', '')
    else:
        project_name = os.path.basename(os.path.abspath(code_directory))
    
    file_structure_list = [f["path"] for f in file_structure["files"]]
    
    code_data = {
        "classes": classes,
        "functions": functions,
        "variables": variables
    }
    
    print(f"  Preparing to generate documentation: {len(classes)} classes, {len(functions)} functions, {len(variables)} variables")
    if len(classes) == 0 and len(functions) == 0:
        print("  Warning: No classes or functions found!")
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
    
    os.makedirs(output_dir, exist_ok=True)
    md_output_path = os.path.join(output_dir, "documentation.md")
    doc_generator.save_markdown(markdown_text, md_output_path)
    
    print("\n" + "=" * 60)
    print("Documentation generation completed!")
    print(f"   Markdown: {md_output_path}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="AutoDoc - Code Documentation Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python autodoc.py code/
  python autodoc.py code/ --output docs/
  python autodoc.py code/ --filter controller,api
  python autodoc.py example.py --filter ""
        """
    )
    
    parser.add_argument(
        "directory",
        type=str,
        help="Path to the code directory or Python file to analyze"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        "--filter",
        type=str,
        default="controller,api,route,endpoint,handler,service",
        help="File filter keywords (comma-separated), only scan files containing these keywords (default: controller,api,route,endpoint,handler,service)"
    )
    
    args = parser.parse_args()
    
    # Check if path is a valid directory or Python file
    is_file = os.path.isfile(args.directory) and args.directory.endswith('.py')
    is_dir = os.path.isdir(args.directory)
    
    if not is_file and not is_dir:
        if os.path.exists(args.directory):
            print(f"Error: '{args.directory}' is not a Python file or directory")
        else:
            print(f"Error: Path '{args.directory}' does not exist")
        return 1
    
    try:
        generate_documentation(
            code_directory=args.directory,
            output_dir=args.output,
            file_filter_keywords=args.filter
        )
        return 0
    except KeyboardInterrupt:
        print("\n\nUser interrupted")
        return 1
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

