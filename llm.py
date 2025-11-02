import pandas as pd
import ollama

# Load CSV
df = pd.read_csv("./data_clean/classes.csv")

def search_information(query):
    # Search the 'Class Name' column for the query
    matches = df[df['Class Name'].str.contains(query, case=False, na=False)]

    if matches.empty:
        return "No results found."

    # Combine matches into a context string
    context = "\n".join(matches.apply(lambda row: f"{row['Class Name']} | {row['File']} | Lines {row['Start Line']}-{row['End Line']}", axis=1))

    # Ask Ollama to summarize / answer
    prompt = f"Use the following class information to answer the question:\n\n{context}\n\nQuestion: {query}\nAnswer:"
    messages = [{"role": "user", "content": prompt}]
    response = ollama.chat(model="llama3:latest", messages=messages)
    return response['message']['content']

# Interactive search
if __name__ == "__main__":
    while True:
        q = input("Enter your query (or 'exit' to quit): ")
        if q.lower() == "exit":
            break
        answer = search_information(q)
        print("\n✅ Answer:\n", answer)
        print("-" * 50)
