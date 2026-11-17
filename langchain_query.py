from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from vector_store import VectorStore
from typing import Dict, List, Optional
from config import get_config, LLMConfig
from alive_progress import alive_bar
from token_counter import get_token_counter
from elements import element_id as make_element_id, is_same_element

try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    ChatGroq = None

PROMPT_TEMPLATE = """Please explain in detail the functionality, parameters, return values, and implementation logic of the following code.

Related context code:
{context}

Current code:
{code}

Please provide a detailed explanation in English of this code's functionality, parameters, return values (if any), implementation logic, and purpose. If the code is incomplete, please make reasonable inferences based on the context."""


class LangChainQuery:
    """Use LangChain + LLM (Ollama/Groq) for RAG queries, process functions/classes one by one"""
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize LangChain query handler
        
        Args:
            vector_store: VectorStore instance
        """
        self.vector_store = vector_store
        self.config = get_config()
        
        provider = self.config.get_provider()
        if provider == LLMConfig.PROVIDER_GROQ:
            if not GROQ_AVAILABLE:
                raise ImportError("langchain-groq is not installed. Please run: pip install langchain-groq")
            api_key = self.config.get_groq_api_key()
            if not api_key:
                raise ValueError("Groq API Key is not set. Please set the GROQ_API_KEY environment variable or configure it in the .env file.")
            self.llm = ChatGroq(
                groq_api_key=api_key,
                model_name=self.config.groq_model,
                temperature=0.1
            )
        else:
            self.llm = Ollama(model=self.config.ollama_model, base_url=self.config.ollama_base_url)
        
        self.prompt = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["context", "code"]
        )
    
    def explain_code_element(
        self, 
        code_text: str, 
        element_name: str,
        element_type: str,
        file_name: str,
        top_k: int = 3,
        class_name: str = ""
    ) -> str:
        """
        Generate explanation for a single code element (function/class)
        
        Args:
            code_text: Source code of the current code element
            element_name: Code element name (function name or class name)
            element_type: Type ("function" or "class")
            file_name: File name
            top_k: Number of related code snippets to retrieve from vector database
            class_name: Enclosing class for methods ("" otherwise)
        
        Returns:
            LLM-generated explanation text
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
            
            # Filter out current element itself. Compare metadata, not text:
            # the stored text has a "def name" header and docstring prepended,
            # so it never equals the raw snippet.
            context_snippets = []
            for result in similar_results:
                if not is_same_element(result["metadata"], file_name, element_type, element_name, class_name):
                    context_snippets.append(result["text"])
                    if len(context_snippets) >= top_k:
                        break
            
            if context_snippets:
                context = "\n\n---\n\n".join(context_snippets)
            else:
                context = "No related context code."
            
            # Build prompt
            prompt = self.prompt.format(context=context, code=code_text)
            
            # Call LLM to generate explanation
            response = self.llm.invoke(prompt)
            
            # Extract text content from response (handle both string and AIMessage objects)
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Track token usage
            token_counter = get_token_counter()
            provider = self.config.get_provider()
            
            if provider == LLMConfig.PROVIDER_GROQ and hasattr(response, 'response_metadata'):
                # Groq provides token usage in metadata
                usage = response.response_metadata.get('token_usage', {})
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                model_name = self.config.groq_model
                token_counter.add_usage(input_tokens, output_tokens, model_name, "explanation")
            else:
                # Ollama doesn't provide token count, estimate it
                input_tokens = token_counter.estimate_tokens(prompt)
                output_tokens = token_counter.estimate_tokens(response_text)
                model_name = self.config.ollama_model
                token_counter.add_usage(input_tokens, output_tokens, model_name, "explanation")
            
            return response_text.strip()
            
        except Exception as e:
            return f"Error generating explanation: {str(e)}"
    
    def batch_explain(
        self,
        code_elements: List[Dict]
    ) -> Dict[str, str]:
        """
        Batch process code elements, generate explanation for each element
        
        Args:
            code_elements: List of dicts, each containing:
                - name: Element name
                - type: "function" or "class"
                - file: File name
                - code: Source code
        
        Returns:
            Dict mapping element_id -> explanation
        """
        explanations = {}
        total = len(code_elements)
        
        with alive_bar(total) as bar:
            for element in code_elements:
                class_name = element.get("class_name") or ""
                element_id = make_element_id(element["file"], element["type"], element["name"], class_name)
                
                explanation = self.explain_code_element(
                    code_text=element["code"],
                    element_name=element["name"],
                    element_type=element["type"],
                    file_name=element["file"],
                    top_k=3,
                    class_name=class_name
                )
                
                explanations[element_id] = explanation
                bar()
        
        return explanations

