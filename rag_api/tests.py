"""Unit tests for RAG system."""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from rag_api.core.models import Repository, Document, Chunk
from rag_api.ingestion.chunking import SemanticChunker
from rag_api.retrieval.bm25_index import BM25Manager
import json


class SemanticChunkerTest(TestCase):
    """Test semantic chunking."""
    
    def setUp(self):
        self.chunker = SemanticChunker(chunk_size=100, overlap=20)
    
    def test_markdown_chunking(self):
        """Test markdown document chunking."""
        content = """# Section 1

This is the first section with some content.

## Subsection 1.1

More content here.

# Section 2

Final section."""
        
        chunks = self.chunker.chunk(content, 'md')
        self.assertGreater(len(chunks), 0)
        self.assertGreater(chunks[0].token_count, 0)
    
    def test_python_code_chunking(self):
        """Test Python code chunking."""
        content = """def function1():
    '''First function.'''
    return "value1"

def function2():
    '''Second function.'''
    return "value2"

class MyClass:
    '''A class.'''
    def method(self):
        pass
"""
        
        chunks = self.chunker.chunk(content, 'py')
        self.assertGreater(len(chunks), 0)


class BM25ManagerTest(TestCase):
    """Test BM25 indexing."""
    
    def setUp(self):
        self.bm25 = BM25Manager()
    
    def test_build_index(self):
        """Test index building."""
        documents = [
            ("doc1", "Python is a programming language"),
            ("doc2", "Django is a web framework"),
            ("doc3", "PostgreSQL is a database"),
        ]
        
        self.bm25.build_index(documents)
        
        self.assertEqual(self.bm25.corpus_size, 3)
        self.assertGreater(len(self.bm25.idf_map), 0)
        self.assertGreater(self.bm25.avg_doc_len, 0)
    
    def test_search(self):
        """Test BM25 search."""
        documents = [
            ("doc1", "Python programming language tutorial"),
            ("doc2", "Django web framework guide"),
            ("doc3", "PostgreSQL database query optimization"),
        ]
        
        self.bm25.build_index(documents)
        results = self.bm25.search("Python", top_k=2)
        
        self.assertGreater(len(results), 0)
        # First result should have highest score
        if len(results) > 1:
            self.assertGreaterEqual(results[0][1], results[1][1])


class RepositoryModelTest(TestCase):
    """Test Repository model."""
    
    def test_create_repository(self):
        """Test repository creation."""
        repo = Repository.objects.create(
            owner="vercel",
            name="next.js",
            url="https://github.com/vercel/next.js",
            branch="main",
        )
        
        self.assertEqual(str(repo), "vercel/next.js")
        self.assertEqual(repo.owner, "vercel")
    
    def test_unique_constraint(self):
        """Test unique constraint on owner+name."""
        Repository.objects.create(
            owner="vercel",
            name="next.js",
            url="https://github.com/vercel/next.js",
        )
        
        with self.assertRaises(Exception):
            Repository.objects.create(
                owner="vercel",
                name="next.js",
                url="https://github.com/vercel/next.js",
            )


class DocumentModelTest(TestCase):
    """Test Document model."""
    
    def setUp(self):
        self.repo = Repository.objects.create(
            owner="vercel",
            name="next.js",
            url="https://github.com/vercel/next.js",
        )
    
    def test_create_document(self):
        """Test document creation."""
        doc = Document.objects.create(
            repository=self.repo,
            file_path="docs/getting-started.md",
            content="# Getting Started\n\nThis is a guide.",
            file_type="md",
            sha256_hash="abc123",
        )
        
        self.assertEqual(doc.file_path, "docs/getting-started.md")
        self.assertEqual(doc.repository, self.repo)


class ChunkModelTest(TestCase):
    """Test Chunk model."""
    
    def setUp(self):
        self.repo = Repository.objects.create(
            owner="vercel",
            name="next.js",
            url="https://github.com/vercel/next.js",
        )
        self.doc = Document.objects.create(
            repository=self.repo,
            file_path="docs/guide.md",
            content="Content",
            file_type="md",
            sha256_hash="xyz789",
        )
    
    def test_create_chunk(self):
        """Test chunk creation."""
        chunk = Chunk.objects.create(
            document=self.doc,
            content="This is chunk content.",
            chunk_index=0,
            start_line=1,
            end_line=10,
            token_count=5,
        )
        
        self.assertEqual(chunk.chunk_index, 0)
        self.assertEqual(chunk.document, self.doc)


class HealthCheckTest(TestCase):
    """Test health check endpoint."""
    
    def setUp(self):
        self.client = Client()
    
    def test_health_check(self):
        """Test health check returns 200."""
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('documents', data)
        self.assertIn('chunks', data)


class RepositoryAPITest(TestCase):
    """Test Repository API endpoints."""
    
    def setUp(self):
        self.client = Client()
    
    def test_list_repositories(self):
        """Test listing repositories."""
        Repository.objects.create(
            owner="vercel",
            name="next.js",
            url="https://github.com/vercel/next.js",
        )
        
        response = self.client.get('/api/repositories/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 1)
    
    def test_stats_endpoint(self):
        """Test stats endpoint."""
        response = self.client.get('/api/repositories/stats/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['repositories'], 0)
