"""GitHub repository loader and ingestion."""
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple
import hashlib
from github import Github
from github.GithubException import GithubException


class GitHubLoader:
    """Load and index repositories from GitHub."""
    
    SUPPORTED_EXTENSIONS = {
        '.md', '.rst', '.txt',  # Documentation
        '.py', '.js', '.ts', '.jsx', '.tsx',  # Code
        '.java', '.cpp', '.c', '.go', '.rs',
        '.json', '.yaml', '.yml', '.toml', '.xml',  # Config
    }
    
    MAX_FILE_SIZE = 1024 * 1024  # 1MB
    
    def __init__(self, token: str = None):
        """Initialize GitHub loader."""
        token = token or os.getenv('GITHUB_TOKEN')
        self.github = Github(token) if token else Github()
    
    def load_repository(self, owner: str, repo_name: str, 
                       branch: str = 'main') -> Tuple[str, List[Tuple[str, str, str]]]:
        """
        Clone and load a GitHub repository.
        
        Returns:
            Tuple of (temp_dir, list of (file_path, content, file_type))
        """
        try:
            repo = self.github.get_user(owner).get_repo(repo_name)
        except GithubException as e:
            raise ValueError(f"Failed to access {owner}/{repo_name}: {str(e)}")
        
        # Create temp directory for cloning
        temp_dir = tempfile.mkdtemp()
        files = []
        
        try:
            # Use GitHub API to get file tree instead of cloning
            contents = repo.get_contents("", ref=branch)
            files = self._fetch_files(repo, contents, branch, "")
        except GithubException as e:
            raise ValueError(f"Failed to fetch repository contents: {str(e)}")
        finally:
            # Clean up temp dir if we created one but didn't use it
            if not files and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        
        return temp_dir, files
    
    def _fetch_files(self, repo, contents, branch: str, 
                     prefix: str = "") -> List[Tuple[str, str, str]]:
        """Recursively fetch files from repository."""
        files = []
        
        for content in contents:
            file_path = content.path
            
            # Skip hidden files and common exclusions
            if any(part.startswith('.') for part in file_path.split('/')):
                continue
            if any(skip in file_path for skip in 
                   ['node_modules', '__pycache__', '.git', 'dist', 'build']):
                continue
            
            if content.type == "dir":
                try:
                    sub_contents = repo.get_contents(file_path, ref=branch)
                    files.extend(self._fetch_files(repo, sub_contents, branch, prefix))
                except GithubException:
                    continue
            elif content.type == "file":
                ext = Path(file_path).suffix.lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    # Check file size
                    if hasattr(content, 'size') and content.size > self.MAX_FILE_SIZE:
                        continue
                    
                    try:
                        file_content = content.decoded_content.decode('utf-8', errors='replace')
                        file_type = ext.lstrip('.')
                        files.append((file_path, file_content, file_type))
                    except Exception:
                        continue
        
        return files
    
    @staticmethod
    def compute_file_hash(content: str) -> str:
        """Compute SHA256 hash of file content."""
        return hashlib.sha256(content.encode()).hexdigest()


class RepositoryMetadata:
    """Metadata about a repository."""
    
    def __init__(self, owner: str, name: str, url: str, branch: str = 'main'):
        self.owner = owner
        self.name = name
        self.url = url
        self.branch = branch
