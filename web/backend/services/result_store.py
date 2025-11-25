import os
import json
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime

class ResultStore:
    """
    Simple file-based persistence for simulation results.
    Saves results as JSON files in a specified directory.
    """
    def __init__(self, storage_dir: str = "web/backend/data/results"):
        self.storage_dir = storage_dir
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        """Ensure the storage directory exists."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)

    def _get_file_path(self, task_id: str) -> str:
        """Get the file path for a given task ID."""
        return os.path.join(self.storage_dir, f"{task_id}.json")

    def save(self, task_id: str, result: Dict[str, Any]):
        """
        Save a simulation result to disk.
        
        Args:
            task_id: The unique identifier for the task.
            result: The simulation result dictionary.
        """
        self._ensure_storage_dir() # Ensure directory exists before saving
        file_path = self._get_file_path(task_id)
        try:
            # Ensure result is JSON serializable
            # Numpy arrays should have been converted to lists already by the engine
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving result for task {task_id}: {e}")
            # Fallback or re-raise depending on requirements. 
            # For now, we just log to console.

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a simulation result from disk.
        
        Args:
            task_id: The unique identifier for the task.
            
        Returns:
            The result dictionary if found, else None.
        """
        file_path = self._get_file_path(task_id)
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading result for task {task_id}: {e}")
            return None

    def list_all(self) -> List[str]:
        """List all stored task IDs."""
        if not os.path.exists(self.storage_dir):
            return []
        
        files = [f for f in os.listdir(self.storage_dir) if f.endswith('.json')]
        # Sort by modification time (newest first)
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.storage_dir, x)), reverse=True)
        return [f.replace('.json', '') for f in files]

    def delete(self, task_id: str):
        """Delete a simulation result."""
        file_path = self._get_file_path(task_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting result for task {task_id}: {e}")

# Global instance
# Adjust path relative to project root if needed, assuming running from root
result_store = ResultStore(storage_dir=os.path.join("web", "backend", "data", "results"))
