import os
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from typing import List, Dict, Tuple, Optional
import uuid
from alive_progress import alive_bar

VECTOR_DB_PATH = "data_clean/chroma_db"


class VectorStore:
    """Manage Chroma vector database for storing code snippets"""
    
    def __init__(self, persist_directory: str = VECTOR_DB_PATH):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        print("    Load embedding model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        print("    Embedding model loaded")

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

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
        """Initialize LangChain Chroma vectorstore"""
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )
    
    def add_code_elements(self, code_elements: List[Dict]):
        """
        Import code to ChromaDB
        
        Args:
            code_elements: List of dicts, each containing:
                - text: code itself
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
        
        num_batches = (total + chroma_batch_size - 1) // chroma_batch_size
        print(f"    Generating embeddings and storing ({total} elements, {num_batches} batches)...")
        
        with alive_bar(num_batches) as bar:
            for i in range(0, total, chroma_batch_size):
                batch_texts = texts[i:i+chroma_batch_size]
                batch_metadatas = metadatas[i:i+chroma_batch_size]
                batch_ids = ids[i:i+chroma_batch_size]
                
                self.vectorstore.add_texts(
                    texts=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                
                bar()
        
        print(f"    Added {total} code elements to vector database")
    
    def search_similar(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar code snippets
        
        Args:
            query: Query text
            top_k: Return top k most similar results
            filter_dict: Optional filter conditions (e.g., {"file": "example.py"})
        
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
        """Clear the vector database"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Code elements (classes, functions) for RAG"}
            )
            self._init_vectorstore()
            print("Vector database cleared")
        except Exception as e:
            print(f"Error clearing vector database: {e}")
    
    def get_stats(self) -> Dict:
        """Get vector database statistics"""
        count = self.collection.count()
        return {
            "total_elements": count
        }

