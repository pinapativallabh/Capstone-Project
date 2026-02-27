import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="data/chroma_db")

embedding_fn = embedding_functions.OllamaEmbeddingFunction(
    model_name="nomic-embed-text",
    url="http://localhost:11434"
)

def get_collection(collection_name="faculty_material"):
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn
    )
