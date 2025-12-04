import ollama
from database import (
    search_classes, search_functions, search_variables,
    get_class_with_details, get_statistics
)
from config import get_config, LLMConfig

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None


def search_information(query, search_type="all"):
    context_parts = []
    
    if search_type in ["all", "class"]:
        classes = search_classes(query)
        if classes:
            context_parts.append("=== Classes ===")
            for cls in classes:
                context_parts.append(f"Class: {cls[0]} | File: {cls[1]} | Lines: {cls[2]}-{cls[3]}")
    
    if search_type in ["all", "function"]:
        functions = search_functions(query)
        if functions:
            context_parts.append("\n=== Functions ===")
            for func in functions:
                class_info = f" (in class: {func[2]})" if func[2] else ""
                context_parts.append(f"Function: {func[0]} | File: {func[1]}{class_info} | Lines: {func[3]}-{func[4]}")
    
    if search_type in ["all", "variable"]:
        variables = search_variables(query)
        if variables:
            context_parts.append("\n=== Variables ===")
            for var in variables[:10]:
                location = f"{var[2]}.{var[3]}" if var[2] and var[3] else (var[2] or var[3] or "global")
                context_parts.append(f"Variable: {var[0]} | File: {var[1]} | Location: {location} | Line: {var[4]}")
            if len(variables) > 10:
                context_parts.append(f"... {len(variables) - 10} more matches")
    
    if not context_parts:
        return "No matching results found."
    
    context = "\n".join(context_parts)
    
    prompt = f"""Answer the question based on the following codebase information:

{context}

Question: {query}

Please provide a clear answer with relevant code locations."""
    
    try:
        config = get_config()
        provider = config.get_provider()
        
        if provider == LLMConfig.PROVIDER_GROQ:

            api_key = config.get_groq_api_key()
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=config.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return response.choices[0].message.content
        else:
            messages = [{"role": "user", "content": prompt}]
            response = ollama.chat(model=config.ollama_model, messages=messages)
            return response['message']['content']
    except Exception as e:
        return f"LLM call failed: {str(e)}"


def show_statistics():
    stats = get_statistics()
    print("\nCodebase Statistics:")
    print(f"  - Classes: {stats['classes']}")
    print(f"  - Functions: {stats['functions']}")
    print(f"  - Variables: {stats['variables']}")
    print(f"  - Files: {stats['files']}")


if __name__ == "__main__":
    print("Codebase Intelligent Query Tool")
    print("Tip: Type 'stats' to view statistics, 'exit' to quit\n")
    
    show_statistics()
    
    while True:
        q = input("\nEnter your query (or 'exit' to quit, 'stats' to view statistics): ").strip()
        
        if q.lower() == "exit":
            break
        elif q.lower() == "stats":
            show_statistics()
            continue
        elif not q:
            continue
        
        print("\nSearch type: [1]All [2]Class [3]Function [4]Variable (default: 1)")
        search_type_input = input("Select: ").strip()
        search_type_map = {
            "1": "all",
            "2": "class",
            "3": "function",
            "4": "variable"
        }
        search_type = search_type_map.get(search_type_input, "all")
        
        answer = search_information(q, search_type)
        print("\nAnswer:\n", answer)
        print("-" * 50)
