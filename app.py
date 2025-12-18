#!/usr/bin/env python3
"""
AutoDoc Streamlit Web Interface
Provides a user-friendly web interface for generating code documentation
"""
import os
import sys
import streamlit as st
import traceback
from pathlib import Path

# Set environment variables
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Import project modules
from autodoc import generate_documentation
from document_generator import DocumentGenerator
from token_counter import get_token_counter
from config import get_config, LLMConfig

# Page configuration
st.set_page_config(
    page_title="AutoDoc - Code Documentation Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="main-header">📚 AutoDoc</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">LLM-Powered Code Documentation Generator</div>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.markdown("---")
    st.subheader("🤖 LLM Settings")
    
    # Load current config
    config = get_config()
    
    # LLM Provider selection
    llm_provider = st.selectbox(
        "LLM Provider",
        options=["Groq", "Ollama"],
        index=0 if config.get_provider() == "groq" else 1,
        help="Choose between Groq (cloud) or Ollama (local)"
    )
    
    if llm_provider == "Groq":
        # Groq configuration
        groq_api_key = st.text_input(
            "Groq API Key",
            value=config.groq_api_key if config.groq_api_key else "",
            type="password",
            help="Enter your Groq API key from console.groq.com"
        )
        
        # Available Groq models
        groq_models = [
            "openai/gpt-oss-120b",
            "qwen/qwen3-32b",
            "meta-llama/llama-4-maverick-17b-128e-instruct"
        ]
        
        current_model_index = 0
        if config.groq_model in groq_models:
            current_model_index = groq_models.index(config.groq_model)
        
        groq_model = st.selectbox(
            "Groq Model",
            options=groq_models,
            index=current_model_index,
            help="Select the Groq model to use"
        )
        
        # Update config if changed
        if groq_api_key and (groq_api_key != config.groq_api_key or groq_model != config.groq_model):
            config.set_groq_config(groq_api_key, groq_model)
            st.session_state['llm_config_updated'] = True
        
        # Show API key status
        if groq_api_key:
            st.success("✅ API Key configured")
        else:
            st.warning("⚠️ Please enter your Groq API Key")
    
    else:
        # Ollama configuration
        ollama_model = st.text_input(
            "Ollama Model",
            value=config.ollama_model,
            help="Enter the Ollama model name (e.g., llama3.2, mistral)"
        )
        
        ollama_base_url = st.text_input(
            "Ollama Base URL",
            value=config.ollama_base_url,
            help="Ollama server URL (default: http://localhost:11434)"
        )
        
        # Update config if changed
        if ollama_model != config.ollama_model or ollama_base_url != config.ollama_base_url:
            config.set_ollama_config(ollama_model, ollama_base_url)
            st.session_state['llm_config_updated'] = True
        
        st.info("💡 Make sure Ollama is running locally")
    
    st.markdown("---")
    st.subheader("📁 Directory Settings")
    
    # Code directory input
    code_dir = st.text_input(
        "Python Project Directory Path",
        placeholder="e.g., /path/to/your/project",
        help="Enter the full path to the Python project you want to analyze"
    )
    
    # Quick select example directory
    if st.button("📂 Use Example Directory (code/)"):
        code_dir = os.path.join(os.getcwd(), "code")
        st.rerun()
    
    # Output directory
    output_dir = st.text_input(
        "Output Directory",
        value="output",
        help="Location where generated documentation will be saved"
    )
    
    st.markdown("---")
    st.subheader("🔍 Filter Settings")
    
    # File filter keywords
    filter_keywords = st.text_input(
        "File Filter Keywords (comma-separated)",
        value="controller,api,route,endpoint,handler,service",
        help="Only analyze files containing these keywords"
    )
    
    # Whether to use filter
    use_filter = st.checkbox(
        "Enable File Filtering",
        value=True,
        help="If disabled, all Python files will be analyzed"
    )
    
    st.markdown("---")
    st.subheader("📄 Output Format")
    
    # PDF generation option
    generate_pdf = st.checkbox(
        "Generate PDF Document",
        value=False,
        help="Also generate PDF format (requires WeasyPrint dependencies)"
    )
    
    st.markdown("---")
    st.markdown("### 💡 Quick Tips")
    st.info("""
    1. Enter project directory path
    2. Configure filter options (optional)
    3. Click "Generate Documentation"
    4. Wait for processing to complete
    5. Preview and download documents
    """)

# Main interface
st.markdown("---")

# Validate input
if not code_dir:
    st.markdown('<div class="info-box">👈 Please enter project directory path on the left to get started</div>', unsafe_allow_html=True)
    
    # Show usage instructions
    st.markdown("## 📖 How to Use")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 1️⃣ Select Directory")
        st.write("Enter the Python project directory path on the left")
    
    with col2:
        st.markdown("### 2️⃣ Configure Options")
        st.write("Set filter keywords and output format")
    
    with col3:
        st.markdown("### 3️⃣ Generate Docs")
        st.write("Click generate button and wait for completion")
    
    st.markdown("---")
    st.markdown("## ✨ Key Features")
    
    features = """
    - 🔍 **Smart Code Analysis**: Automatically extract classes, functions, variables
    - 🤖 **AI-Powered Explanations**: Generate detailed code descriptions using LLM
    - 📊 **Vector Search**: Semantic similarity-based code understanding
    - 📝 **Multiple Formats**: Support Markdown and PDF output
    - 🎯 **Flexible Filtering**: Customize which files to analyze
    - 🚀 **Batch Processing**: Efficiently handle large projects
    """
    st.markdown(features)
    
else:
    # Check if path is a valid directory or Python file
    is_file = os.path.isfile(code_dir) and code_dir.endswith('.py')
    is_dir = os.path.isdir(code_dir)
    
    if not is_file and not is_dir:
        if os.path.exists(code_dir):
            st.markdown(f'<div class="error-box">❌ Error: "{code_dir}" is not a Python file or directory. Please check the path.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="error-box">❌ Error: Path "{code_dir}" does not exist. Please check the path.</div>', unsafe_allow_html=True)
    else:
        # Display path information
        if is_file:
            st.markdown(f'<div class="info-box">📄 Single File Mode: <code>{code_dir}</code></div>', unsafe_allow_html=True)
            st.write(f"📊 Analyzing **1** Python file")
        else:
            st.markdown(f'<div class="info-box">📁 Project Directory: <code>{code_dir}</code></div>', unsafe_allow_html=True)
            
            # Count Python files
            py_files = list(Path(code_dir).rglob("*.py"))
            st.write(f"📊 Detected **{len(py_files)}** Python files")
        
        # Generate button
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            generate_button = st.button(
                "🚀 Generate Documentation",
                type="primary",
                use_container_width=True
            )
        
        # Handle generation logic
        if generate_button:
            # Clear previous state
            if 'markdown_content' in st.session_state:
                del st.session_state['markdown_content']
            if 'pdf_path' in st.session_state:
                del st.session_state['pdf_path']
            
            # Reset token counter for new generation
            token_counter = get_token_counter()
            token_counter.reset()
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Progress display
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_container = st.expander("📋 Detailed Logs", expanded=True)
            
            try:
                with log_container:
                    log_area = st.empty()
                    logs = []
                    
                    def add_log(message):
                        logs.append(message)
                        log_area.text("\n".join(logs))
                    
                    # Step 1: Initialize
                    status_text.text("⏳ [1/6] Initializing database...")
                    progress_bar.progress(10)
                    add_log("[1/6] Initializing database...")
                    
                    # Step 2-6: Generate documentation
                    status_text.text("⏳ [2/6] Scanning and analyzing code...")
                    progress_bar.progress(20)
                    add_log("[2/6] Scanning and analyzing code...")
                    
                    # Call generation function
                    if use_filter:
                        filter_str = filter_keywords
                    else:
                        filter_str = ""  # Empty string means no filter
                    
                    # Redirect stdout to capture logs
                    import io
                    from contextlib import redirect_stdout
                    
                    f = io.StringIO()
                    with redirect_stdout(f):
                        generate_documentation(
                            code_directory=code_dir,
                            output_dir=output_dir,
                            file_filter_keywords=filter_str if filter_str else "."  # Use . to match all files
                        )
                    
                    output = f.getvalue()
                    for line in output.split('\n'):
                        if line.strip():
                            add_log(line)
                    
                    progress_bar.progress(80)
                    
                    # Read generated Markdown
                    md_path = os.path.join(output_dir, "documentation.md")
                    if os.path.exists(md_path):
                        with open(md_path, "r", encoding="utf-8") as f:
                            markdown_content = f.read()
                        st.session_state['markdown_content'] = markdown_content
                        st.session_state['md_path'] = md_path
                        add_log(f"✅ Markdown document generated: {md_path}")
                    
                    # Generate PDF (if requested)
                    if generate_pdf:
                        status_text.text("⏳ [7/7] Generating PDF document...")
                        progress_bar.progress(90)
                        add_log("[7/7] Generating PDF document...")
                        
                        try:
                            doc_generator = DocumentGenerator()
                            pdf_path = os.path.join(output_dir, "documentation.pdf")
                            doc_generator.markdown_to_pdf(markdown_content, pdf_path)
                            st.session_state['pdf_path'] = pdf_path
                            add_log(f"✅ PDF document generated: {pdf_path}")
                        except Exception as e:
                            add_log(f"⚠️ PDF generation failed: {str(e)}")
                            add_log("Tip: Make sure WeasyPrint dependencies are installed")
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Documentation generation complete!")
                    
                    # Display token usage statistics
                    token_counter = get_token_counter()
                    config = get_config()
                    provider = config.get_provider()
                    
                    if provider == LLMConfig.PROVIDER_GROQ:
                        model_key = f"groq_{config.groq_model}"
                    else:
                        model_key = "ollama"
                    
                    summary = token_counter.get_summary(model_key)
                    
                    # Store summary in session state for display
                    st.session_state['token_summary'] = summary
                    st.session_state['model_key'] = model_key
                    
                    add_log("\n" + "=" * 50)
                    add_log("Token Usage Summary")
                    add_log("=" * 50)
                    add_log(f"Total LLM Calls: {summary['total_calls']}")
                    add_log(f"Input Tokens:    {summary['total_input_tokens']:,}")
                    add_log(f"Output Tokens:   {summary['total_output_tokens']:,}")
                    add_log(f"Total Tokens:    {summary['total_tokens']:,}")
                    
                    if summary['estimated_cost_usd'] > 0:
                        add_log(f"\nEstimated Cost:  ${summary['estimated_cost_usd']:.4f} USD")
                    else:
                        add_log("\nCost: $0.00 (Local model)")
                    add_log("=" * 50)
                    
                st.success("🎉 Documentation generated successfully!")
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.markdown(f'<div class="error-box">❌ Generation failed: {str(e)}</div>', unsafe_allow_html=True)
                
                with st.expander("🔍 Error Details"):
                    st.code(traceback.format_exc())
        
        # Display generation results
        if 'markdown_content' in st.session_state:
            st.markdown("---")
            st.markdown("## 📄 Generated Results")
            
            # Display token statistics if available
            if 'token_summary' in st.session_state:
                st.markdown("### 📊 Token Usage Statistics")
                summary = st.session_state['token_summary']
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Tokens", f"{summary['total_tokens']:,}")
                with col2:
                    st.metric("Input Tokens", f"{summary['total_input_tokens']:,}")
                with col3:
                    st.metric("Output Tokens", f"{summary['total_output_tokens']:,}")
                with col4:
                    st.metric("LLM Calls", f"{summary['total_calls']}")
                
                # Cost and model display
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Estimated Cost", f"${summary['estimated_cost_usd']:.4f}")
                with col2:
                    st.metric("Avg Tokens/Call", f"{summary['total_tokens'] / max(summary['total_calls'], 1):.0f}")
                with col3:
                    model_key = st.session_state.get('model_key', 'unknown')
                    model_display = model_key.replace('groq_', '').replace('ollama', 'Local')
                    st.metric("Model", model_display)
                
                st.markdown("---")
            
            # Download buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    label="📥 Download Markdown",
                    data=st.session_state['markdown_content'],
                    file_name="documentation.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col2:
                if 'pdf_path' in st.session_state and os.path.exists(st.session_state['pdf_path']):
                    with open(st.session_state['pdf_path'], "rb") as f:
                        pdf_bytes = f.read()
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name="documentation.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.button("📥 Download PDF", disabled=True, use_container_width=True)
            
            with col3:
                if st.button("🗑️ Clear Results", use_container_width=True):
                    if 'markdown_content' in st.session_state:
                        del st.session_state['markdown_content']
                    if 'pdf_path' in st.session_state:
                        del st.session_state['pdf_path']
                    if 'md_path' in st.session_state:
                        del st.session_state['md_path']
                    st.rerun()
            
            # Markdown preview
            st.markdown("---")
            st.markdown("### 📖 Markdown Preview")
            
            # Preview options
            preview_mode = st.radio(
                "Preview Mode",
                ["Rendered View", "Source Code View"],
                horizontal=True
            )
            
            if preview_mode == "Rendered View":
                # Limit preview length to avoid performance issues
                content = st.session_state['markdown_content']
                if len(content) > 50000:
                    st.warning(f"⚠️ Document is large ({len(content)} characters), showing first 50000 characters only")
                    content = content[:50000] + "\n\n... (Content truncated, please download full document)"
                
                st.markdown(content, unsafe_allow_html=False)
            else:
                # Source code view
                st.code(st.session_state['markdown_content'], language="markdown")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <p>AutoDoc - AI-Powered Code Documentation Generator | Powered by LangChain & Streamlit</p>
</div>
""", unsafe_allow_html=True)

