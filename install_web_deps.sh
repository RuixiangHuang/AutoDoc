#!/bin/bash
# 安装 Web 界面依赖

echo "=========================================="
echo "  安装 AutoDoc Web 界面依赖"
echo "=========================================="
echo ""

# 检查虚拟环境
if [[ -f "venv/bin/activate" ]]; then
    echo "✅ 检测到虚拟环境"
    PYTHON="venv/bin/python"
    PIP="venv/bin/pip"
else
    echo "⚠️  未检测到虚拟环境，使用系统 Python"
    PYTHON="python3"
    PIP="pip3"
fi

echo ""
echo "📦 安装 Streamlit..."
$PIP install streamlit

echo ""
echo "📦 检查其他依赖..."
$PIP install -r requirements.txt

echo ""
echo "=========================================="
echo "  ✅ 安装完成！"
echo "=========================================="
echo ""
echo "现在可以运行:"
echo "  ./run_app.sh"
echo "或:"
echo "  streamlit run app.py"
echo ""

