# AutoDoc - AI-Powered Code Documentation Generator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io/)

AutoDoc is an intelligent code documentation generation system that uses AI to automatically analyze Python projects and generate comprehensive, well-structured documentation in Markdown and PDF formats.

## ✨ Features

- 🔍 **Smart Code Analysis**: Automatically extracts classes, functions, variables, and their relationships
- 🤖 **AI-Powered Explanations**: Uses LLM (Ollama/Groq) to generate detailed, contextual code descriptions
- 📊 **Vector Search**: Semantic similarity-based code understanding using ChromaDB
- 📝 **Multiple Output Formats**: Supports both Markdown and PDF documentation
- 🎯 **Flexible Filtering**: Customize which files to analyze (e.g., only API/controller files)
- 🚀 **Batch Processing**: Efficiently handles large codebases
- 🌐 **Web Interface**: User-friendly Streamlit web UI for easy operation
- 📖 **Real-time Preview**: View generated documentation instantly in the browser

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Ollama (for local LLM) or Groq API key (for cloud LLM)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd AutoDoc
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure LLM settings**

Create or edit `env.config`:
```ini
# Option 1: Use Ollama (local)
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2

# Option 2: Use Groq (cloud)
LLM_PROVIDER=groq
GROQ_API_KEY=your_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

### Usage

#### Option 1: Web Interface (Recommended)

1. **Install web dependencies**
```bash
chmod +x install_web_deps.sh
./install_web_deps.sh
```

2. **Launch the web interface**
```bash
./run_app.sh
# Or directly: streamlit run app.py
```

3. **Use the interface**
   - Open browser at `http://localhost:8501`
   - Enter your project directory path
   - Configure filter options (optional)
   - Click "Generate Documentation"
   - Preview and download the generated docs

#### Option 2: Command Line

```bash
python autodoc.py <project_directory> [options]

# Examples:
python autodoc.py ./my-project
python autodoc.py ./my-project --output docs/
python autodoc.py ./my-project --filter controller,api,route
```

**Command line options:**
- `--output, -o`: Output directory (default: `output`)
- `--filter`: File filter keywords, comma-separated (default: `controller,api,route,endpoint,handler,service`)

## 📖 How It Works

1. **Code Analysis**: Scans Python files and extracts code elements (classes, functions, variables)
2. **Database Storage**: Stores code structure in SQLite for efficient querying
3. **Vector Embedding**: Generates embeddings for semantic search using sentence-transformers
4. **AI Explanation**: Uses LLM to generate detailed explanations for each code element
5. **Document Generation**: Compiles everything into well-formatted Markdown/PDF documentation

## 🎯 Use Cases

- **API Documentation**: Automatically document REST APIs, controllers, and endpoints
- **Code Onboarding**: Help new team members understand the codebase quickly
- **Knowledge Base**: Create searchable documentation for large projects
- **Code Review**: Generate summaries for code review processes
- **Technical Debt**: Document legacy code that lacks documentation

## 📁 Project Structure

```
AutoDoc/
├── app.py                      # Streamlit web interface
├── autodoc.py                  # Main CLI entry point
├── main.py                     # Code analysis module
├── database.py                 # SQLite database operations
├── vector_store.py             # ChromaDB vector storage
├── langchain_query.py          # LLM query and explanation
├── document_generator.py       # Markdown/PDF generation
├── elements.py                 # Shared code-element IDs
├── tests/                      # Regression tests (stdlib unittest)
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── run_app.sh                  # Web interface launcher
└── install_web_deps.sh         # Dependency installer
```

## ⚙️ Configuration

### LLM Provider Options

**Ollama (Local)**
- Free and private
- Requires local installation
- Models: llama3.2, mistral, etc.

**Groq (Cloud)**
- Fast inference
- Requires API key
- Models: llama-3.3-70b-versatile, mixtral-8x7b, etc.

### File Filtering

By default, AutoDoc filters files by keywords to focus on interface/API files:
- `controller`
- `api`
- `route`
- `endpoint`
- `handler`
- `service`

You can customize this in the web interface or via command line `--filter` option.

To analyze all Python files, disable filtering in the web interface or use `--filter ""`.

## 🔧 Advanced Usage

### Custom Analysis

Edit `main.py` to customize:
- Code element extraction logic
- File filtering rules
- Code snippet length limits

### Custom Documentation Templates

Edit `document_generator.py` to customize:
- Document structure
- Styling (for PDF output)
- Section ordering
- Language/localization

### Vector Store Configuration

Edit `vector_store.py` to configure:
- Embedding model
- ChromaDB settings
- Similarity search parameters

## 📊 Performance Tips

1. **Use File Filtering**: Analyze only relevant files to save time
2. **First Run**: Initial run downloads embedding model (~400MB), subsequent runs are faster
3. **Large Projects**: Consider processing in batches by module/directory
4. **PDF Generation**: Optional and slower; generate Markdown first to verify content

## 🐛 Troubleshooting

### Issue: "Module not found" errors
**Solution**: Make sure all dependencies are installed
```bash
pip install -r requirements.txt
```

### Issue: PDF generation fails
**Solution**: Install WeasyPrint system dependencies

**macOS:**
```bash
brew install cairo pango gdk-pixbuf libffi
pip install weasyprint
```

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0
pip install weasyprint
```

### Issue: Ollama connection error
**Solution**: Make sure Ollama is running
```bash
ollama serve
ollama pull llama3.2
```

### Issue: Slow processing
**Causes**:
- First run downloads embedding model
- Large codebase requires more time
- LLM inference can be slow

**Solutions**:
- Use file filtering to reduce scope
- Use Groq for faster LLM inference
- Be patient on first run

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

Run the tests (no LLM or extra packages needed):
```bash
python -m unittest discover -s tests
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) - LLM orchestration framework
- [Streamlit](https://streamlit.io/) - Web interface framework
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [Groq](https://groq.com/) - Fast LLM inference
- [Sentence Transformers](https://www.sbert.net/) - Embedding models

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation in the `docs/` folder
- Review the troubleshooting section above

---

**AutoDoc** - Making code documentation effortless with AI! 🚀✨

