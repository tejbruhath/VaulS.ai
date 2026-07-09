"""Citation and source attribution utilities."""
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
import re


@dataclass
class Citation:
    """Represents a citation reference."""
    file_path: str
    start_line: int
    end_line: int
    repository: str
    url: str = ""
    
    def __str__(self):
        """Format as readable citation."""
        return f"{self.file_path} (lines {self.start_line}-{self.end_line})"
    
    def __hash__(self):
        return hash((self.file_path, self.start_line, self.end_line))
    
    def __eq__(self, other):
        if not isinstance(other, Citation):
            return False
        return (self.file_path == other.file_path and 
                self.start_line == other.start_line and 
                self.end_line == other.end_line)


class CitationFormatter:
    """Format citations in different styles."""
    
    @staticmethod
    def format_markdown(citations: List[Citation]) -> str:
        """Format citations as Markdown."""
        if not citations:
            return ""
        
        output = "\n## Sources\n\n"
        for i, citation in enumerate(citations, 1):
            output += f"{i}. [{citation.file_path}]({citation.url or '#'})"
            output += f" - Lines {citation.start_line}-{citation.end_line}\n"
        
        return output
    
    @staticmethod
    def format_html(citations: List[Citation]) -> str:
        """Format citations as HTML."""
        if not citations:
            return ""
        
        html = "<div class='citations'><h3>Sources:</h3><ol>"
        for citation in citations:
            url = f"<a href='{citation.url}'>" if citation.url else "<span>"
            close_tag = "</a>" if citation.url else "</span>"
            html += f"<li>{url}{citation.file_path}{close_tag} (lines {citation.start_line}-{citation.end_line})</li>"
        html += "</ol></div>"
        
        return html
    
    @staticmethod
    def format_json(citations: List[Citation]) -> List[Dict]:
        """Format citations as JSON."""
        return [
            {
                "file_path": c.file_path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "repository": c.repository,
                "url": c.url,
            }
            for c in citations
        ]
    
    @staticmethod
    def format_bibtex(citations: List[Citation]) -> str:
        """Format citations as BibTeX."""
        bibtex = ""
        for i, citation in enumerate(citations, 1):
            bibtex += f"""@inproceedings{{source{i},
    title={{{citation.file_path}}},
    note={{Lines {citation.start_line}-{citation.end_line}}},
    url={{{citation.url}}}
}}

"""
        return bibtex


class InlineCircationExtractor:
    """Extract inline citations from text."""
    
    @staticmethod
    def extract_citations_from_text(text: str) -> List[str]:
        """Extract citation patterns from text."""
        # Match [SOURCE: file.path (lines X-Y)] patterns
        pattern = r'\[SOURCE:\s*([^\]]+)\s*\(lines?\s*(\d+)-(\d+)\)\]'
        matches = re.findall(pattern, text)
        return matches
    
    @staticmethod
    def remove_inline_citations(text: str) -> str:
        """Remove inline citation markers from text."""
        pattern = r'\[SOURCE:\s*[^\]]+\s*\(lines?\s*\d+-\d+\)\]\n?'
        return re.sub(pattern, '', text)


class CitationValidator:
    """Validate citations for correctness."""
    
    @staticmethod
    def validate_citation(citation: Citation) -> Tuple[bool, List[str]]:
        """
        Validate a citation.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not citation.file_path:
            errors.append("File path cannot be empty")
        
        if citation.start_line < 0:
            errors.append("Start line cannot be negative")
        
        if citation.end_line < citation.start_line:
            errors.append("End line must be >= start line")
        
        if len(citation.file_path) > 500:
            errors.append("File path too long")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def deduplicate_citations(citations: List[Citation]) -> List[Citation]:
        """Remove duplicate citations."""
        seen = set()
        unique = []
        
        for citation in citations:
            if citation not in seen:
                seen.add(citation)
                unique.append(citation)
        
        return unique
    
    @staticmethod
    def merge_adjacent_citations(citations: List[Citation]) -> List[Citation]:
        """Merge citations from same file that are adjacent."""
        if not citations:
            return []
        
        # Sort by file path and start line
        sorted_cites = sorted(citations, 
                             key=lambda c: (c.file_path, c.start_line))
        
        merged = []
        current = sorted_cites[0]
        
        for next_cite in sorted_cites[1:]:
            if (current.file_path == next_cite.file_path and
                current.end_line + 1 >= next_cite.start_line):
                # Merge
                current = Citation(
                    file_path=current.file_path,
                    start_line=current.start_line,
                    end_line=max(current.end_line, next_cite.end_line),
                    repository=current.repository,
                    url=current.url,
                )
            else:
                merged.append(current)
                current = next_cite
        
        merged.append(current)
        return merged


class SourceAttributionBuilder:
    """Build source attribution from retrieved chunks."""
    
    @staticmethod
    def build_from_chunks(chunks_metadata: List[Dict]) -> List[Citation]:
        """Build citations from chunk metadata."""
        citations = []
        
        for metadata in chunks_metadata:
            citation = Citation(
                file_path=metadata.get('file_path', 'unknown'),
                start_line=metadata.get('start_line', 0),
                end_line=metadata.get('end_line', 0),
                repository=metadata.get('repository', ''),
                url=metadata.get('url', ''),
            )
            
            # Validate before adding
            is_valid, _ = CitationValidator.validate_citation(citation)
            if is_valid:
                citations.append(citation)
        
        # Deduplicate and merge
        citations = CitationValidator.deduplicate_citations(citations)
        citations = CitationValidator.merge_adjacent_citations(citations)
        
        return citations
    
    @staticmethod
    def format_for_context(citations: List[Citation]) -> str:
        """Format citations for inclusion in LLM context."""
        if not citations:
            return ""
        
        context = "Based on the following sources:\n\n"
        for citation in citations:
            context += f"- {str(citation)}\n"
        
        context += "\n"
        return context
