"""
FastMCP 2.0 Server - Book Tools MCP Server

A practical MCP server that provides tools for working with books.
This server demonstrates core FastMCP concepts including:
- Tool definition and registration
- Type hints and automatic schema generation
- Multiple tool implementations
- Error handling
- Resources for data exposure
- Prompts for user guidance
"""

import os
import json
from pathlib import Path
from datetime import datetime
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Book Tools Server", version="1.0.0")

# Path to books directory
BOOKS_DIR = Path(__file__).parent.parent / "4_rag" / "books"


@mcp.tool
def list_available_books() -> dict:
    """List all available books in the library."""
    if not BOOKS_DIR.exists():
        return {"books": [], "count": 0, "error": "Books directory not found"}
    
    books = []
    for book_file in sorted(BOOKS_DIR.glob("*.txt")):
        books.append({
            "name": book_file.stem,
            "filename": book_file.name,
            "size_kb": round(book_file.stat().st_size / 1024, 2)
        })
    
    return {
        "books": books,
        "count": len(books)
    }


@mcp.tool
def get_book_content(book_name: str, max_lines: int = 50) -> dict:
    """Get the content of a specific book, limited to max_lines."""
    book_path = BOOKS_DIR / f"{book_name}.txt"
    
    if not book_path.exists():
        return {
            "error": f"Book '{book_name}' not found",
            "available_books": [b.stem for b in BOOKS_DIR.glob("*.txt")]
        }
    
    try:
        with open(book_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        content = ''.join(lines[:max_lines])
        return {
            "book": book_name,
            "lines_returned": min(max_lines, len(lines)),
            "total_lines": len(lines),
            "content": content
        }
    except Exception as e:
        return {"error": f"Failed to read book: {str(e)}"}


@mcp.tool
def search_in_book(book_name: str, search_term: str) -> dict:
    """Search for a term in a specific book and return matching lines."""
    book_path = BOOKS_DIR / f"{book_name}.txt"
    
    if not book_path.exists():
        return {"error": f"Book '{book_name}' not found"}
    
    try:
        with open(book_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Search for matching lines (case-insensitive)
        search_lower = search_term.lower()
        matches = []
        for i, line in enumerate(lines, 1):
            if search_lower in line.lower():
                matches.append({
                    "line_number": i,
                    "content": line.strip()
                })
        
        # Limit results to first 20 matches
        return {
            "book": book_name,
            "search_term": search_term,
            "matches_found": len(matches),
            "matches": matches[:20],
            "truncated": len(matches) > 20
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}


@mcp.tool
def get_book_statistics(book_name: str) -> dict:
    """Get statistics about a book including word count and basic metrics."""
    book_path = BOOKS_DIR / f"{book_name}.txt"
    
    if not book_path.exists():
        return {"error": f"Book '{book_name}' not found"}
    
    try:
        with open(book_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        words = content.split()
        characters = len(content)
        
        # Find average word length
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
        
        return {
            "book": book_name,
            "total_lines": len(lines),
            "total_words": len(words),
            "total_characters": characters,
            "average_word_length": round(avg_word_length, 2),
            "size_mb": round(characters / (1024 * 1024), 3)
        }
    except Exception as e:
        return {"error": f"Failed to calculate statistics: {str(e)}"}


@mcp.tool
def get_book_preview(book_name: str, lines: int = 10) -> dict:
    """Get a quick preview of the first N lines of a book."""
    book_path = BOOKS_DIR / f"{book_name}.txt"
    
    if not book_path.exists():
        return {"error": f"Book '{book_name}' not found"}
    
    try:
        with open(book_path, 'r', encoding='utf-8', errors='ignore') as f:
            preview = []
            for i, line in enumerate(f):
                if i >= lines:
                    break
                preview.append(line.rstrip())
        
        return {
            "book": book_name,
            "preview_lines": len(preview),
            "content": '\n'.join(preview)
        }
    except Exception as e:
        return {"error": f"Failed to get preview: {str(e)}"}


@mcp.tool
def compare_books(book1: str, book2: str) -> dict:
    """Compare statistics between two books."""
    books = [book1, book2]
    stats = {}
    
    for book in books:
        book_path = BOOKS_DIR / f"{book}.txt"
        if not book_path.exists():
            return {"error": f"Book '{book}' not found"}
        
        try:
            with open(book_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            words = content.split()
            stats[book] = {
                "word_count": len(words),
                "character_count": len(content),
                "line_count": len(content.split('\n'))
            }
        except Exception as e:
            return {"error": f"Failed to read book {book}: {str(e)}"}
    
    # Calculate differences
    word_diff = stats[book2]["word_count"] - stats[book1]["word_count"]
    char_diff = stats[book2]["character_count"] - stats[book1]["character_count"]
    
    return {
        "book1": book1,
        "book2": book2,
        "stats": stats,
        "differences": {
            "word_count_diff": word_diff,
            "word_count_percentage": round((word_diff / stats[book1]["word_count"] * 100), 2) if stats[book1]["word_count"] > 0 else 0,
            "character_count_diff": char_diff
        }
    }


# ============================================================================
# RESOURCES - Expose book data and catalogs
# ============================================================================

@mcp.resource(
    uri="books://catalog",
    name="Book Catalog",
    description="Complete catalog of all available books with metadata",
    mime_type="application/json"
)
def get_book_catalog() -> str:
    """Provides a complete catalog of all available books."""
    if not BOOKS_DIR.exists():
        return json.dumps({
            "books": [],
            "count": 0,
            "error": "Books directory not found"
        })
    
    books = []
    for book_file in sorted(BOOKS_DIR.glob("*.txt")):
        try:
            with open(book_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            words = content.split()
            books.append({
                "name": book_file.stem,
                "filename": book_file.name,
                "size_kb": round(book_file.stat().st_size / 1024, 2),
                "word_count": len(words),
                "line_count": len(content.split('\n'))
            })
        except Exception as e:
            continue
    
    return json.dumps({
        "books": books,
        "count": len(books),
        "last_updated": datetime.now().isoformat()
    })


@mcp.resource(
    uri="books://featured",
    name="Featured Books",
    description="Selection of featured books for quick access",
    mime_type="application/json"
)
def get_featured_books() -> str:
    """Provides a curated selection of featured books."""
    featured = ["moby_dick", "pride_and_prejudice", "iliad", "odyssey"]
    return json.dumps({
        "featured_books": featured,
        "description": "A curated selection of classic literature available in the library",
        "featured_date": datetime.now().isoformat()
    })


@mcp.resource(
    uri="books://search-guide",
    name="Search Guide",
    description="Guide for searching and filtering books effectively",
    mime_type="text/plain"
)
def get_search_guide() -> str:
    """Provides guidance on how to search books effectively."""
    return """BOOK SEARCH GUIDE
================

Available Operations:

1. LIST BOOKS
   Use the "list_available_books" tool to see all books in the library.

2. SEARCH IN BOOKS
   Use "search_in_book" to find specific terms across book content.
   - Supports case-insensitive search
   - Returns up to 20 matching lines per book
   - Useful for finding key passages and themes

3. GET BOOK PREVIEW
   Use "get_book_preview" to view the first N lines of any book.
   - Default: First 10 lines
   - Good for understanding book formatting and content

4. GET BOOK STATISTICS
   Use "get_book_statistics" to analyze:
   - Total word and line counts
   - Character count and text metrics
   - Average word length
   - File size information

5. COMPARE BOOKS
   Use "compare_books" to analyze differences:
   - Word count comparison
   - Character count analysis
   - Statistical metrics

TIPS:
- Search is case-insensitive for convenience
- Book names use underscores (e.g., "pride_and_prejudice")
- Large books (>1000 words) may need filtered searches
- Use statistics to understand book complexity
"""


# ============================================================================
# PROMPTS - Guide users on how to use the book tools
# ============================================================================

@mcp.prompt(
    name="analyze_book",
    description="Template for analyzing a book's content and structure"
)
def analyze_book_prompt() -> str:
    """Prompt template for comprehensive book analysis."""
    return """I want to analyze a classic book. Here's my analysis framework:

1. OVERVIEW
   - Book title and author
   - Quick statistics (word count, line count)
   - Overall structure and length

2. CONTENT EXPLORATION
   - Search for key themes or characters
   - Find important passages
   - Identify recurring words or phrases

3. STYLISTIC ANALYSIS
   - Compare this book with another similar work
   - Analyze word length and complexity
   - Review literary devices and language

4. INSIGHTS
   - What makes this book significant?
   - How does it compare to contemporary literature?

To get started, use the available tools:
- list_available_books() - See all books
- get_book_statistics(book_name) - Get metrics
- search_in_book(book_name, search_term) - Find content
- compare_books(book1, book2) - Compare works
"""


@mcp.prompt(
    name="compare_books",
    description="Guide for comparing two books and their characteristics"
)
def compare_books_prompt() -> str:
    """Prompt template for book comparison."""
    return """I want to compare two classic works of literature. Here's what I'll examine:

1. BASIC METRICS
   - Word count comparison
   - Length and complexity
   - File sizes and content volume

2. STYLISTIC DIFFERENCES
   - Vocabulary and language complexity
   - Sentence and paragraph structure
   - Writing style characteristics

3. THEMATIC EXPLORATION
   - Search for similar themes in both books
   - Compare character names and types
   - Analyze common literary elements

4. CONCLUSION
   - Which book is more complex?
   - How do writing styles differ?
   - Which book might be easier to read?

Use these tools:
- compare_books(book1, book2) - Get statistical comparison
- search_in_book(book_name, search_term) - Search both books
- get_book_statistics(book_name) - Get individual metrics

Start by selecting two books from the available catalog."""


@mcp.prompt(
    name="book_search_workflow",
    description="Workflow for finding and extracting information from books"
)
def book_search_workflow_prompt() -> str:
    """Prompt template for book searching."""
    return """I want to search for and extract specific information from books.

WORKFLOW:

1. DISCOVER
   - List all available books: list_available_books()
   - Preview book beginnings: get_book_preview(book_name)
   - Get featured recommendations from the "Featured Books" resource

2. SEARCH
   - Search for specific terms: search_in_book(book_name, search_term)
   - Case-insensitive searching is supported
   - Explore themes, characters, or specific passages

3. ANALYZE
   - Get book statistics: get_book_statistics(book_name)
   - Understand complexity and scope
   - Compare multiple books: compare_books(book1, book2)

4. EXTRACT
   - View full content: get_book_content(book_name, max_lines)
   - Focus on specific sections
   - Export relevant passages for analysis

TIPS FOR EFFECTIVE SEARCHING:
- Use multiple search terms to find variations
- Combine tools for deeper analysis
- Check featured books for popular recommendations
- Use statistics to understand scope before deep diving

Ready to search? Start with list_available_books() or check the available resources!
"""


if __name__ == "__main__":
    # Run the server with stdio transport (default)
    # Use transport="http" and port=8000 for HTTP transport
    mcp.run()
