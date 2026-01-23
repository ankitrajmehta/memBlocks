import requests
import json
from concurrent.futures import ThreadPoolExecutor


class OllamaEmbeddings:

    def __init__(self, model = "nomic-embed-text", base_url = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.embeddings_endpoint = f"{base_url}/api/embeddings"

    def embed_text(self, text):
        payload = {
            "model": self.model,
            "prompt": text
        }
        try:
            response = requests.post(
                self.embeddings_endpoint,
                json = payload,
                timeout = 30
            )
            response.raise_for_status()

            result = response.json()
            return result.get("embedding")

        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise
            

    def embed_documents(self, texts):
        # using ThreadPoolExecutor for parallel embedding (2 times faster cha)
        with ThreadPoolExecutor(max_workers=min(10, len(texts))) as executor:
            return list(executor.map(self.embed_text, texts))

    def get_dimension(self):
        sample_embedding = self.embed_text("test")
        return len(sample_embedding)

# Test the embeddings
if __name__ == "__main__":
    print("🧪 Testing Ollama embeddings...")
    timings = []
    embedder = OllamaEmbeddings()
    import time

    for _ in range(50):
        start = time.time()
        # Test single embedding
        text = "This is a testing sentence"
        embedding = embedder.embed_text(text)
        end = time.time()
        timings.append(end - start)
    avg_time = sum(timings) / len(timings)
    print(f"⏱️ Average time taken by request: {avg_time:.2f} seconds")
    print(f"✅ Generated embedding for: '{text}'")
    print(f"   Dimension: {len(embedding)}")
    print(f"   First 5 values: {embedding[:5]}")

    timings = []
    for _ in range(51):
        # Test batch embedding
        texts = [
            "This is the first testing sentence.",
            "Here is another sentence for embedding.",
            "Embeddings are useful for many applications.",
            "This is a sample text to test batch embedding.",
            "Ollama provides local embedding generation."
        ]
        start = time.time()
        embeddings = embedder.embed_documents(texts)
        timings.append(time.time() - start)
    avg_time = sum(timings) / len(timings)  
    print(f"\n⏱️ Average time taken for batch embedding of {len(texts)} texts: {avg_time:.2f} seconds")
    
    # Get dimension
    dim = embedder.get_dimension()
    print(f"\n📏 Embedding dimension: {dim}")


