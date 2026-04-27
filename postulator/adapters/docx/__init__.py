from .adapter import DocxAdapter

# Backward-compat aliases
DocxWriter = DocxAdapter
DocxReader = DocxAdapter

__all__ = ["DocxAdapter", "DocxWriter", "DocxReader"]
