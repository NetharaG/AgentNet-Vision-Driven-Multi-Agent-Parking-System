from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import uuid
import chromadb

class VectorStore(ABC):
    """
    Abstract Base Class for Vector Database interactions.
    """
    @abstractmethod
    def upsert_vector(self, vehicle_id: str, embedding: List[float], metadata: Dict = None):
        pass

    @abstractmethod
    def search_vehicle(self, embedding: List[float], threshold: float = 0.85) -> Optional[str]:
        pass

class ChromaVectorStore(VectorStore):
    """
    Implementation using ChromaDB (Local Persistent).
    """
    def __init__(self, collection_name: str = "vehicle_appearances"):
        print("[VectorStore] Initializing ChromaDB...")
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name=collection_name)
        print("[VectorStore] ChromaDB Ready.")

    def upsert_vector(self, vehicle_id: str, embedding: List[float], metadata: Dict = None):
        """
        Store a vehicle's feature vector.
        """
        if metadata is None:
            metadata = {}
        
        # Add vehicle_id to metadata for easy retrieval
        metadata["vehicle_id"] = vehicle_id
        
        self.collection.add(
            documents=[vehicle_id], # Using ID as document text for now
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[f"{vehicle_id}_{str(uuid.uuid4())[:8]}"] # Unique ID for this 'sighting'
        )
        print(f"[VectorStore] Upserted embedding for {vehicle_id}")

    def search_vehicle(self, embedding: List[float], threshold: float = 0.85) -> Optional[str]:
        """
        Identify a vehicle by its visual embedding.
        """
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=1
        )
        
        # Chroma returns lists of lists
        if results['ids'] and results['ids'][0] and results['distances'] and results['distances'][0]:
            # Distance is usually L2 or Cosine. Lower might be better depending on metric.
            # Default is L2 (Squared Euclidean). 0.0 is exact match.
            try:
                distance = results['distances'][0][0]
                
                # Arbitrary threshold for demo (e.g., < 0.5 is a match)
                if distance < 0.5: 
                    match_meta = results['metadatas'][0][0]
                    vid = match_meta.get("vehicle_id")
                    print(f"[VectorStore] Match Found! {vid} (Dist: {distance:.4f})")
                    return vid
                else:
                    print(f"[VectorStore] No close match (Nearest: {distance:.4f})")
            except IndexError:
                return None
        
        return None
