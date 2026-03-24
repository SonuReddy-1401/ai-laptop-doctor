import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

class LaptopKnowledgeBase:
    def __init__(self, manuals_path="manuals", db_path="chroma_db"):
        self.manuals_path = manuals_path
        self.db_path = db_path
        # We MUST hardcode this to llama3.2 (or another dedicated embedding model)
        # because the vector database was already built with dimension 3072!
        self.embeddings = OllamaEmbeddings(model="llama3.2")

    def ingest_manuals(self):
        """Reads all 5 PDFs, chunks them, and saves to the local database."""
        if not os.path.exists(self.manuals_path):
            os.makedirs(self.manuals_path)
            print(f"Please put your 5 PDFs in the '{self.manuals_path}' folder first!")
            return

        print(f"--- 1. Loading PDFs from {self.manuals_path} ---")
        loader = DirectoryLoader(self.manuals_path, glob="./*.pdf", loader_cls=PyPDFLoader)
        documents = loader.load()

        if not documents:
            print("No PDFs found. Check your 'manuals' folder.")
            return

        # We split the text into 1000-character chunks
        # This ensures the AI finds the specific page it needs
        print("--- 2. Splitting manuals into searchable chunks ---")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = text_splitter.split_documents(documents)

        print(f"--- 3. Indexing {len(chunks)} chunks into ChromaDB ---")
        self.vector_db = Chroma.from_documents(
            documents=chunks, 
            embedding=self.embeddings, 
            persist_directory=self.db_path
        )
        print("--- SUCCESS: Knowledge Base is Ready! ---")

    def query(self, search_text):
        """Search the database for specific repair steps."""
        db = Chroma(persist_directory=self.db_path, embedding_function=self.embeddings)
        results = db.similarity_search(search_text, k=3)
        return [res.page_content for res in results]

if __name__ == "__main__":
    # MAKE SURE OLLAMA IS RUNNING IN YOUR TASKBAR!
    kb = LaptopKnowledgeBase()
    kb.ingest_manuals()