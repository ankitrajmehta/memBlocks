import requests
import json

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
        return [self.embed_text(text) for text in texts]

    def get_dimension(self):
        sample_embedding = self.embed_text("test")
        return len(sample_embedding)

# Test the embeddings
if __name__ == "__main__":
    print("🧪 Testing Ollama embeddings...")

    embedder = OllamaEmbeddings()

    # Test single embedding
    text = "This is a testing sentence"
    embedding = embedder.embed_text(text)
    print(f"✅ Generated embedding for: '{text}'")
    print(f"   Dimension: {len(embedding)}")
    print(f"   First 5 values: {embedding[:5]}")
    
    # Get dimension
    dim = embedder.get_dimension()
    print(f"\n📏 Embedding dimension: {dim}")


