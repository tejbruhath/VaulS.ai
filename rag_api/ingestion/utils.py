"""Utility functions for ingestion."""
import re
from typing import List, Dict


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    return text.strip()


def extract_markdown_metadata(content: str) -> Dict:
    """Extract metadata from markdown frontmatter."""
    frontmatter_pattern = r'^---\n(.*?)\n---\n'
    match = re.match(frontmatter_pattern, content, re.DOTALL)
    
    metadata = {}
    if match:
        frontmatter = match.group(1)
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()
    
    return metadata


def get_file_type_category(file_type: str) -> str:
    """Get category of file type."""
    doc_types = {'md', 'markdown', 'rst', 'txt', 'adoc'}
    code_types = {'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'go', 'rs', 'rb', 'php'}
    config_types = {'json', 'yaml', 'yml', 'toml', 'xml', 'ini', 'conf'}
    
    if file_type in doc_types:
        return 'documentation'
    elif file_type in code_types:
        return 'code'
    elif file_type in config_types:
        return 'configuration'
    else:
        return 'other'


def estimate_reading_time(text: str) -> int:
    """Estimate reading time in minutes (assuming 200 WPM)."""
    words = len(text.split())
    return max(1, words // 200)


def sanitize_for_embedding(text: str, max_length: int = 8000) -> str:
    """Sanitize text for embedding."""
    # Remove special characters but keep structure
    text = clean_text(text)
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + '...'
    return text


class ChunkingValidator:
    """Validate chunks for quality."""
    
    MIN_CHUNK_SIZE = 50  # Minimum characters
    MAX_CHUNK_SIZE = 10000  # Maximum characters
    
    @classmethod
    def validate_chunk(cls, chunk_text: str) -> Dict:
        """
        Validate a chunk.
        
        Returns:
            Dictionary with 'valid' bool and 'issues' list
        """
        issues = []
        
        if len(chunk_text) < cls.MIN_CHUNK_SIZE:
            issues.append(f"Chunk too small ({len(chunk_text)} chars, min {cls.MIN_CHUNK_SIZE})")
        
        if len(chunk_text) > cls.MAX_CHUNK_SIZE:
            issues.append(f"Chunk too large ({len(chunk_text)} chars, max {cls.MAX_CHUNK_SIZE})")
        
        # Check for repetitive content
        lines = chunk_text.split('\n')
        if len(lines) > 2:
            if len(set(lines)) < len(lines) * 0.5:
                issues.append("High repetition in chunk")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
        }


class RepositoryIngestionValidator:
    """Validate repository for ingestion."""
    
    MAX_FILES = 1000  # Max files per repo
    MAX_FILE_SIZE = 1024 * 1024  # 1MB per file
    MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB total
    
    @classmethod
    def validate(cls, file_count: int, total_size: int) -> Dict:
        """Validate repository ingestion parameters."""
        issues = []
        warnings = []
        
        if file_count > cls.MAX_FILES:
            issues.append(f"Too many files ({file_count}, max {cls.MAX_FILES})")
        
        if total_size > cls.MAX_TOTAL_SIZE:
            issues.append(f"Repository too large ({total_size / 1024 / 1024:.1f}MB, max {cls.MAX_TOTAL_SIZE / 1024 / 1024:.0f}MB)")
        
        if file_count > cls.MAX_FILES * 0.8:
            warnings.append("Repository approaching file limit")
        
        if total_size > cls.MAX_TOTAL_SIZE * 0.8:
            warnings.append("Repository approaching size limit")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
        }
