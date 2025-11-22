from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from vector_store import VectorStore
from typing import Dict, List, Optional

# 中英文提示词模板
CHINESE_PROMPT_TEMPLATE = """请详细解释以下代码的功能、参数、返回值和实现逻辑。

相关上下文代码：
{context}

当前代码：
{code}

请用中文详细解释这段代码的功能、参数、返回值（如果有）、实现逻辑和用途。如果代码不完整，请根据上下文进行合理推断。"""

ENGLISH_PROMPT_TEMPLATE = """Please explain in detail the functionality, parameters, return values, and implementation logic of the following code.

Related context code:
{context}

Current code:
{code}

Please provide a detailed explanation in English of this code's functionality, parameters, return values (if any), implementation logic, and purpose. If the code is incomplete, please make reasonable inferences based on the context."""


class LangChainQuery:
    """使用 LangChain + Ollama 进行 RAG 查询，逐个处理函数/类"""
    
    def __init__(self, vector_store: VectorStore, language: str = "zh"):
        """
        初始化 LangChain 查询器
        
        Args:
            vector_store: VectorStore 实例
            language: 语言选择，"zh" 为中文，"en" 为英文
        """
        self.vector_store = vector_store
        self.language = language
        
        # 初始化 Ollama LLM
        self.llm = Ollama(model="llama3:latest")
        
        # 选择提示词模板
        if language == "zh":
            self.prompt_template = CHINESE_PROMPT_TEMPLATE
        else:
            self.prompt_template = ENGLISH_PROMPT_TEMPLATE
        
        self.prompt = PromptTemplate(
            template=self.prompt_template,
            input_variables=["context", "code"]
        )
    
    def explain_code_element(
        self, 
        code_text: str, 
        element_name: str,
        element_type: str,
        file_name: str,
        top_k: int = 3
    ) -> str:
        """
        为单个代码元素（函数/类）生成解释
        
        Args:
            code_text: 当前代码元素的源代码
            element_name: 代码元素名称（函数名或类名）
            element_type: 类型（"function" 或 "class"）
            file_name: 文件名
            top_k: 从向量数据库检索的相关代码片段数量
        
        Returns:
            LLM 生成的解释文本
        """
        try:
            # 从向量数据库检索相关代码片段
            # 使用元素名称和类型作为查询
            query_text = f"{element_type} {element_name} in {file_name}"
            
            # 排除当前元素本身
            similar_results = self.vector_store.search_similar(
                query=query_text,
                top_k=top_k + 1,  # 多取一个，然后过滤掉自己
                filter_dict=None
            )
            
            # 过滤掉当前元素本身（通过比较代码文本）
            context_snippets = []
            for result in similar_results:
                # 如果代码文本不完全相同，则作为上下文
                if result["text"].strip() != code_text.strip():
                    context_snippets.append(result["text"])
                    if len(context_snippets) >= top_k:
                        break
            
            # 构建上下文
            if context_snippets:
                context = "\n\n---\n\n".join(context_snippets)
            else:
                context = "无相关上下文代码。" if self.language == "zh" else "No related context code."
            
            # 构建提示词
            prompt = self.prompt.format(context=context, code=code_text)
            
            # 调用 LLM 生成解释
            response = self.llm.invoke(prompt)
            
            return response.strip()
            
        except Exception as e:
            error_msg = f"生成解释时出错: {str(e)}" if self.language == "zh" else f"Error generating explanation: {str(e)}"
            return error_msg
    
    def batch_explain(
        self,
        code_elements: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, str]:
        """
        批量处理代码元素，为每个元素生成解释
        
        Args:
            code_elements: List of dicts, each containing:
                - name: 元素名称
                - type: "function" 或 "class"
                - file: 文件名
                - code: 源代码
            progress_callback: 可选的回调函数，接收 (current, total) 参数
        
        Returns:
            Dict mapping element_id -> explanation
        """
        explanations = {}
        total = len(code_elements)
        
        for idx, element in enumerate(code_elements, 1):
            element_id = f"{element['file']}::{element['type']}::{element['name']}"
            
            explanation = self.explain_code_element(
                code_text=element["code"],
                element_name=element["name"],
                element_type=element["type"],
                file_name=element["file"],
                top_k=3
            )
            
            explanations[element_id] = explanation
            
            # 调用进度回调
            if progress_callback:
                progress_callback(idx, total)
        
        return explanations

