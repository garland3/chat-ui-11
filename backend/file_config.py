"""
File handling configuration for managing which files are exposed to LLM context vs tool-only.

This module defines policies for how different file types and sizes should be handled
in the chat interface, particularly what should be exposed to the LLM directly vs
what should only be processed by tools.
"""

from typing import Set, Dict, Any
import logging

logger = logging.getLogger(__name__)

# File types that should only be processed by tools, never exposed to LLM
TOOL_ONLY_FILE_TYPES: Set[str] = {
    # Data files that require specialized processing
    '.csv', '.xlsx', '.xls', '.json', '.jsonl',
    # Binary formats that LLMs cannot interpret
    '.pdf', '.doc', '.docx', '.ppt', '.pptx',
    # Images and media
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
    '.mp3', '.wav', '.flac', '.aac', '.ogg',
    # Code and executable files
    '.exe', '.dll', '.so', '.app', '.deb', '.rpm',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    # Database files
    '.db', '.sqlite', '.sqlite3', '.mdb'
}

# File types that can be mentioned to LLM (small text files)
LLM_VISIBLE_FILE_TYPES: Set[str] = {
    '.txt', '.md', '.rst', '.log'
}

# Maximum file size (in bytes) that can be exposed to LLM context
MAX_LLM_VISIBLE_FILE_SIZE = 1 * 1024  # 1KB

# Maximum file size (in bytes) for any uploaded file
MAX_UPLOAD_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class FilePolicy:
    """Policy for handling file exposure to LLM context."""
    
    def __init__(self):
        self.tool_only_types = TOOL_ONLY_FILE_TYPES.copy()
        self.llm_visible_types = LLM_VISIBLE_FILE_TYPES.copy()
        self.max_llm_size = MAX_LLM_VISIBLE_FILE_SIZE
        self.max_upload_size = MAX_UPLOAD_FILE_SIZE
    
    def should_expose_to_llm(self, filename: str, file_size_bytes: int) -> bool:
        """
        Determine if a file should be exposed to the LLM context.
        
        Args:
            filename: Name of the file
            file_size_bytes: Size of the decoded file content in bytes
            
        Returns:
            True if file should be mentioned in LLM context, False if tool-only
        """
        # Get file extension
        ext = self._get_file_extension(filename)
        
        # Check if it's explicitly tool-only
        if ext in self.tool_only_types:
            logger.debug(f"File {filename} is tool-only type ({ext})")
            return False
        
        # Check if it's explicitly LLM-visible
        if ext in self.llm_visible_types:
            # Still check size limit
            if file_size_bytes > self.max_llm_size:
                logger.debug(f"File {filename} too large for LLM ({file_size_bytes} bytes > {self.max_llm_size})")
                return False
            return True
        
        # For unknown extensions, use size-based policy
        if file_size_bytes > self.max_llm_size:
            logger.debug(f"Unknown file type {filename} too large for LLM ({file_size_bytes} bytes)")
            return False
        
        logger.debug(f"File {filename} ({ext}) allowed in LLM context (size: {file_size_bytes} bytes)")
        return True
    
    def _get_file_extension(self, filename: str) -> str:
        """Get lowercase file extension including the dot."""
        if '.' not in filename:
            return ''
        return '.' + filename.split('.')[-1].lower()
    
    def get_file_category(self, filename: str) -> str:
        """Get a human-readable category for the file type."""
        ext = self._get_file_extension(filename)
        
        if ext in {'.csv', '.xlsx', '.xls', '.json', '.jsonl'}:
            return 'Data file'
        elif ext in {'.pdf', '.doc', '.docx'}:
            return 'Document'
        elif ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}:
            return 'Image'
        elif ext in {'.txt', '.md', '.rst', '.log'}:
            return 'Text file'
        elif ext in {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}:
            return 'Video'
        elif ext in {'.mp3', '.wav', '.flac', '.aac', '.ogg'}:
            return 'Audio'
        else:
            return 'Other'


# Global file policy instance
file_policy = FilePolicy()


def filter_files_for_llm_context(uploaded_files: Dict[str, str]) -> Dict[str, int]:
    """
    Filter uploaded files to determine which should be exposed to LLM context.
    
    Args:
        uploaded_files: Dict mapping filename to base64 content
        
    Returns:
        Dict mapping filename to decoded file size for files that should be exposed to LLM
    """
    import base64
    
    llm_visible_files = {}
    tool_only_files = {}
    
    for filename, base64_content in uploaded_files.items():
        try:
            # Calculate decoded size
            decoded_size = len(base64.b64decode(base64_content))
            
            if file_policy.should_expose_to_llm(filename, decoded_size):
                llm_visible_files[filename] = decoded_size
            else:
                tool_only_files[filename] = decoded_size
                
        except Exception as e:
            logger.warning(f"Could not analyze file {filename}: {e}")
            # Treat unreadable files as tool-only
            tool_only_files[filename] = 0
    
    logger.info(f"File filtering: {len(llm_visible_files)} LLM-visible, {len(tool_only_files)} tool-only")
    if tool_only_files:
        logger.info(f"Tool-only files: {list(tool_only_files.keys())}")
    if llm_visible_files:
        logger.info(f"LLM-visible files: {list(llm_visible_files.keys())}")
        
    return llm_visible_files


def get_supported_file_types() -> str:
    """Get a string listing all supported file types for upload."""
    all_types = TOOL_ONLY_FILE_TYPES.union(LLM_VISIBLE_FILE_TYPES)
    # Remove dots and sort
    types_without_dots = sorted([t[1:] for t in all_types if t.startswith('.')])
    return '.' + ',.' .join(types_without_dots)