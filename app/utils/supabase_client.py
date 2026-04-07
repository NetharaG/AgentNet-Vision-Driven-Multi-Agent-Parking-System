import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()

class SupabaseManager:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseManager, cls).__new__(cls)
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            
            if not url or not key:
                print("[SupabaseManager] CRITICAL: SUPABASE_URL or SUPABASE_KEY missing from .env")
                cls._client = None
            else:
                try:
                    cls._client = create_client(url, key)
                    print("[SupabaseManager] Connection established.")
                except Exception as e:
                    print(f"[SupabaseManager] Connection failed: {e}")
                    cls._client = None
        return cls._instance

    @property
    def client(self) -> Client:
        return self._client

# Global instance for easy import
supabase_manager = SupabaseManager()
