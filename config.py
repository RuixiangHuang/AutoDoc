import os
from typing import Optional

class LLMConfig:
    """LLM configuration management class"""
    
    # LLM provider types
    PROVIDER_OLLAMA = "ollama"
    PROVIDER_GROQ = "groq"
    
    def __init__(self):
        # Read configuration from environment variables, default to ollama
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.model = os.getenv("LLM_MODEL", "qwen3-coder:30b")
        
        # Groq configuration
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        
        # Ollama configuration
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen3-coder:30b")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        # Try to read from .env file (if environment variables are not set)
        self._load_from_env_file()
    
    def _load_from_env_file(self):
        """Load configuration from .env or env.config file"""
        # Try .env first, then env.config
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if not os.path.exists(env_file):
            env_file = os.path.join(os.path.dirname(__file__), "env.config")
        if os.path.exists(env_file):
            try:
                # Simple .env file parsing
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            
                            if key == "LLM_PROVIDER" and not os.getenv("LLM_PROVIDER"):
                                self.provider = value.lower()
                            elif key == "GROQ_API_KEY" and not os.getenv("GROQ_API_KEY"):
                                self.groq_api_key = value
                            elif key == "GROQ_MODEL" and not os.getenv("GROQ_MODEL"):
                                self.groq_model = value
                            elif key == "OLLAMA_MODEL" and not os.getenv("OLLAMA_MODEL"):
                                self.ollama_model = value
                            elif key == "OLLAMA_BASE_URL" and not os.getenv("OLLAMA_BASE_URL"):
                                self.ollama_base_url = value
            except Exception as e:
                print(f"Error reading .env file: {str(e)}")
    
    def get_provider(self) -> str:
        """Get current LLM provider"""
        return self.provider
    
    def get_groq_api_key(self) -> Optional[str]:
        """Get Groq API Key"""
        return self.groq_api_key if self.groq_api_key else None
    
    def validate(self) -> tuple[bool, str]:
        """Validate if configuration is valid"""
        if self.provider == self.PROVIDER_GROQ:
            api_key = self.get_groq_api_key()
            if not api_key:
                return False, "Groq API Key is not set. Please set the GROQ_API_KEY environment variable or configure it in the .env file."
        elif self.provider == self.PROVIDER_OLLAMA:
            # Ollama doesn't require API key, but can check if service is available
            pass
        else:
            return False, f"Unsupported LLM provider: {self.provider}"
        
        return True, "Configuration is valid"


# Global configuration instance
_config = None

def get_config() -> LLMConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = LLMConfig()
    return _config

