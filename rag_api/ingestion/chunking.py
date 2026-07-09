"""Semantic chunking strategies."""
import re
from typing import List, Tuple, Dict
import tiktoken


class ChunkedContent:
    """Represents a semantically chunked document."""
    
    def __init__(self, content: str, chunk_index: int, start_line: int, 
                 end_line: int, token_count: int):
        self.content = content
        self.chunk_index = chunk_index
        self.start_line = start_line
        self.end_line = end_line
        self.token_count = token_count


class SemanticChunker:
    """Chunks documents semantically based on content structure."""
    
    def __init__(self, chunk_size: int = 512, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))
    
    def _split_markdown(self, content: str) -> List[Tuple[str, int, int]]:
        """Split markdown by headers and code blocks, preserving structure."""
        chunks = []
        current_chunk = []
        current_line = 1
        chunk_start_line = 1
        current_tokens = 0
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_tokens = self.count_tokens(line)
            is_header = line.startswith('#')
            is_code_fence = line.strip().startswith('```')
            
            # Check if adding this line would exceed chunk size
            if (current_tokens + line_tokens > self.chunk_size and 
                current_chunk and (is_header or is_code_fence)):
                # Finalize current chunk
                chunk_text = '\n'.join(current_chunk)
                if chunk_text.strip():
                    chunks.append((chunk_text, chunk_start_line, current_line - 1))
                
                # Start new chunk, but include overlap
                overlap_lines = self._get_overlap_lines(current_chunk)
                current_chunk = overlap_lines
                chunk_start_line = max(1, current_line - len(overlap_lines))
                current_tokens = sum(self.count_tokens(l) for l in overlap_lines)
            
            current_chunk.append(line)
            current_tokens += line_tokens
            current_line = i + 2
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            if chunk_text.strip():
                chunks.append((chunk_text, chunk_start_line, current_line - 1))
        
        return chunks
    
    def _split_code(self, content: str) -> List[Tuple[str, int, int]]:
        """Split code by functions/classes and logical sections."""
        chunks = []
        current_chunk = []
        current_line = 1
        chunk_start_line = 1
        current_tokens = 0
        
        lines = content.split('\n')
        
        # Simple heuristic: split on function/class definitions for Python
        function_pattern = re.compile(r'^\s*(def|class|async def)\s+')
        
        for i, line in enumerate(lines):
            line_tokens = self.count_tokens(line)
            is_definition = function_pattern.match(line)
            
            if (current_tokens + line_tokens > self.chunk_size and 
                current_chunk and is_definition):
                chunk_text = '\n'.join(current_chunk)
                if chunk_text.strip():
                    chunks.append((chunk_text, chunk_start_line, current_line - 1))
                
                overlap_lines = self._get_overlap_lines(current_chunk)
                current_chunk = overlap_lines
                chunk_start_line = max(1, current_line - len(overlap_lines))
                current_tokens = sum(self.count_tokens(l) for l in overlap_lines)
            
            current_chunk.append(line)
            current_tokens += line_tokens
            current_line = i + 2
        
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            if chunk_text.strip():
                chunks.append((chunk_text, chunk_start_line, current_line - 1))
        
        return chunks
    
    def _get_overlap_lines(self, lines: List[str]) -> List[str]:
        """Get the last few lines for overlap."""
        overlap_tokens = 0
        overlap_lines = []
        
        for line in reversed(lines):
            line_tokens = self.count_tokens(line)
            if overlap_tokens + line_tokens > self.overlap:
                break
            overlap_lines.insert(0, line)
            overlap_tokens += line_tokens
        
        return overlap_lines
    
    def chunk(self, content: str, file_type: str) -> List[ChunkedContent]:
        """Chunk content based on file type."""
        if file_type in ('md', 'markdown', 'rst'):
            chunks = self._split_markdown(content)
        elif file_type in ('py', 'js', 'ts', 'java', 'cpp', 'go'):
            chunks = self._split_code(content)
        else:
            chunks = self._split_markdown(content)
        
        result = []
        for idx, (chunk_text, start_line, end_line) in enumerate(chunks):
            result.append(ChunkedContent(
                content=chunk_text,
                chunk_index=idx,
                start_line=start_line,
                end_line=end_line,
                token_count=self.count_tokens(chunk_text)
            ))
        
        return result
