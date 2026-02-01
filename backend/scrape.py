from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def ask_bot(query):
    # Initialize embeddings (must match index_data.py)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # Load the persisted Chroma DB
    persist_directory = "./chroma_db"
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
        collection_name="indus_net_knowledge"
    )

    # # Perform similarity search
    results = vectorstore.similarity_search(query, k=2)

    for i, doc in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"Content: {doc.page_content}")
        print(f"Metadata: {doc.metadata}")
    
    formatted_results = []
    for i, doc in enumerate(results):
        content = doc.page_content.strip()
        meta = doc.metadata
        
        # Start with the main content
        md_chunk = f"### Result {i+1}\n\n{content}\n"
        
        # 2. Extract and format ALL metadata dynamically
        details = []
        for key, val in meta.items():
            # Skip internal/empty keys if necessary (e.g., 'source_content_focus')
            if not val or key in ["source_content_focus"]:
                continue

            human_key = key.replace("_", " ").title()
            
            # Check if it's a JSON string (list or dict)
            if isinstance(val, str) and val.strip().startswith(("[", "{")):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        formatted_val = ", ".join(map(str, parsed))
                    elif isinstance(parsed, dict):
                        formatted_val = ", ".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in parsed.items()])
                    else:
                        formatted_val = str(parsed)
                    
                    details.append(f"**{human_key}:** {formatted_val}")
                except:
                    # Fallback for invalid JSON
                    details.append(f"**{human_key}:** {val}")
            else:
                # Regular value
                details.append(f"**{human_key}:** {val}")

        if details:
            md_chunk += "\n" + "\n".join([f"- {d}" for d in details])
        
        formatted_results.append(md_chunk)

    cleaned = "\n\n---\n\n".join(formatted_results)
    print(cleaned)

if __name__ == "__main__":
    ask_bot("what are the services")