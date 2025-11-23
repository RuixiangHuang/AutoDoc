import os
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from typing import List, Dict, Tuple, Optional
import uuid

VECTOR_DB_PATH = "data_clean/chroma_db"


class VectorStore:
    """管理 Chroma 向量数据库，存储代码片段"""
    
    def __init__(self, persist_directory: str = VECTOR_DB_PATH):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # 使用 HuggingFace 的嵌入模型（sentence-transformers）
        # 这个模型不需要特定的 Ollama 模型支持嵌入功能
        # 首次使用时会自动下载模型
        print("    正在加载嵌入模型...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        print("    ✅ 嵌入模型加载完成")
        
        # 初始化 Chroma 客户端
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 创建或获取集合
        self.collection_name = "code_elements"
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Code elements (classes, functions) for RAG"}
            )
        
        # LangChain Chroma wrapper
        self.vectorstore = None
        self._init_vectorstore()
    
    def _init_vectorstore(self):
        """初始化 LangChain Chroma vectorstore"""
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )
    
    def add_code_elements(self, code_elements: List[Dict]):
        """
        添加代码元素到向量数据库
        
        Args:
            code_elements: List of dicts, each containing:
                - text: 代码文本
                - metadata: dict with file, name, type, start_line, end_line, class_name, etc.
        """
        if not code_elements:
            return
        
        texts = [elem["text"] for elem in code_elements]
        metadatas = [elem["metadata"] for elem in code_elements]
        ids = [str(uuid.uuid4()) for _ in code_elements]
        
        # ChromaDB batch size limit (safe value set to 5000)
        total = len(texts)
        chroma_batch_size = 5000  # Less than ChromaDB's maximum batch size 5461
        
        print(f"    Generating embeddings and storing ({total} elements, {(total + chroma_batch_size - 1) // chroma_batch_size} batches)...")
        
        # Process in batches to avoid exceeding ChromaDB batch limit
        processed = 0
        for i in range(0, total, chroma_batch_size):
            batch_texts = texts[i:i+chroma_batch_size]
            batch_metadatas = metadatas[i:i+chroma_batch_size]
            batch_ids = ids[i:i+chroma_batch_size]
            
            # Generate embeddings and store
            self.vectorstore.add_texts(
                texts=batch_texts,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            
            processed = min(i + chroma_batch_size, total)
            print(f"    Processed: {processed}/{total} ({processed*100//total}%)")
        
        print(f"    ✅ Added {total} code elements to vector database")
    
    def search_similar(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        搜索相似的代码片段
        
        Args:
            query: 查询文本
            top_k: 返回最相似的前 k 个结果
            filter_dict: 可选的过滤条件（如 {"file": "example.py"}）
        
        Returns:
            List of dicts with 'text', 'metadata', 'score'
        """
        if filter_dict:
            where = filter_dict
        else:
            where = None
        
        results = self.vectorstore.similarity_search_with_score(
            query=query,
            k=top_k,
            filter=where
        )
        
        return [
            {
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]
    
    def clear(self):
        """清空向量数据库"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Code elements (classes, functions) for RAG"}
            )
            self._init_vectorstore()
            print("✅ Vector database cleared")
        except Exception as e:
            print(f"⚠️ Error clearing vector database: {e}")
    
    def get_stats(self) -> Dict:
        """获取向量数据库统计信息"""
        count = self.collection.count()
        return {
            "total_elements": count
        }

