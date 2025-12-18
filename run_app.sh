#!/bin/bash
# AutoDoc Streamlit Application Startup Script

echo "=========================================="
echo "  AutoDoc - Code Documentation Generator"
echo "=========================================="
echo ""

# Check if in virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Virtual environment not detected"
    echo "It's recommended to activate virtual environment first:"
    echo "  source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if streamlit is installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "❌ Streamlit not installed"
    echo "Installing dependencies..."
    pip install streamlit
fi

echo ""
echo "🚀 Starting AutoDoc Web Interface..."
echo "📱 Browser will automatically open at http://localhost:8501"
echo ""
echo "Tip: Press Ctrl+C to stop the server"
echo ""

# Start streamlit
streamlit run app.py

