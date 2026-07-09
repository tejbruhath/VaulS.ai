#!/usr/bin/env python
"""Index multiple GitHub repositories."""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from rag_api.ingestion.tasks import index_repository

# Repositories to index
REPOS_TO_INDEX = [
    ('vercel', 'next.js', 'main'),
    ('python', 'cpython', 'main'),
    ('openai', 'openai-python', 'main'),
]

if __name__ == '__main__':
    print("Starting repository indexing...")
    
    for owner, name, branch in REPOS_TO_INDEX:
        print(f"\nIndexing {owner}/{name} ({branch})...")
        task = index_repository.delay(owner, name, branch)
        print(f"Task ID: {task.id}")
        
        # Optional: wait for task to complete
        # result = task.get(timeout=3600)
        # print(f"Result: {result}")
    
    print("\nIndexing tasks submitted. Monitor progress in Celery worker logs.")
