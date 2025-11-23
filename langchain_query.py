from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
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
    """Use LangChain + Ollama for RAG queries, process functions/classes one by one"""
    
    def __init__(self, vector_store: VectorStore, language: str = "en"):
        """
        Initialize LangChain query handler
        
        Args:
            vector_store: VectorStore instance
            language: Language selection, "zh" for Chinese, "en" for English
        """
        self.vector_store = vector_store
        self.language = language
        
        # 初始化 Ollama LLM
        self.llm = Ollama(model="qwen3-coder:30b")
        
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
            # Retrieve related code snippets from vector database
            # Use element name and type as query
            query_text = f"{element_type} {element_name} in {file_name}"
            
            # Exclude current element itself
            similar_results = self.vector_store.search_similar(
                query=query_text,
                top_k=top_k + 1,  # Get one more, then filter out self
                filter_dict=None
            )
            
            # Filter out current element itself (by comparing code text)
            context_snippets = []
            for result in similar_results:
                # If code text is not exactly the same, use as context
                if result["text"].strip() != code_text.strip():
                    context_snippets.append(result["text"])
                    if len(context_snippets) >= top_k:
                        break
            
            # Build context
            if context_snippets:
                context = "\n\n---\n\n".join(context_snippets)
            else:
                context = "No related context code." if self.language == "en" else "无相关上下文代码。"
            
            # Build prompt
            prompt = self.prompt.format(context=context, code=code_text)
            
            # Call LLM to generate explanation
            response = self.llm.invoke(prompt)
            
            return response.strip()
            
        except Exception as e:
            error_msg = f"Error generating explanation: {str(e)}" if self.language == "en" else f"生成解释时出错: {str(e)}"
            return error_msg
    
    def batch_explain(
        self,
        code_elements: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, str]:
        """
        Batch process code elements, generate explanation for each element
        
        Args:
            code_elements: List of dicts, each containing:
                - name: Element name
                - type: "function" or "class"
                - file: File name
                - code: Source code
            progress_callback: Optional callback function, receives (current, total) parameters
        
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

