#!/usr/bin/env python3
"""
Export search results to HTML for viewing in browser
Usage: python export_search.py "search term" 
Opens results in browser automatically
"""

import sys
import webbrowser
from pathlib import Path
from search_intelligence.basic_search import search as perform_search
import html
import re
from datetime import datetime

def clean_content(text):
    """Remove HTML tags and clean up content"""
    # First decode HTML entities
    text = html.unescape(text)
    # Remove HTML tags
    text = re.sub('<[^<]+?>', '', text)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def export_to_html(query, limit=20):
    results = perform_search(query, limit=limit)
    
    if not results:
        print("No results found")
        return
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Search Results: {html.escape(query)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .result {{
            background: white;
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .result:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        .title {{
            font-size: 18px;
            font-weight: bold;
            color: #1a73e8;
            margin-bottom: 8px;
        }}
        .metadata {{
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .content {{
            color: #333;
            line-height: 1.6;
            max-height: 300px;
            overflow-y: auto;
        }}
        .highlight {{
            background: yellow;
            padding: 2px 4px;
            border-radius: 2px;
        }}
        .expand-btn {{
            color: #1a73e8;
            cursor: pointer;
            text-decoration: underline;
            font-size: 14px;
            margin-top: 10px;
            display: inline-block;
        }}
    </style>
    <script>
        function toggleContent(id, fullContent, previewContent) {{
            var element = document.getElementById('content-' + id);
            var button = document.getElementById('btn-' + id);
            var isExpanded = button.textContent === 'Show less';
            
            if (isExpanded) {{
                // Show preview
                element.textContent = previewContent;
                element.style.maxHeight = '300px';
                button.textContent = 'Show full content';
            }} else {{
                // Show full content
                element.textContent = fullContent;
                element.style.maxHeight = 'none';
                button.textContent = 'Show less';
            }}
        }}
    </script>
</head>
<body>
    <h1>Search Results: "{html.escape(query)}"</h1>
    <p style="color: #666;">{len(results)} results found - {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
"""

    for i, result in enumerate(results):
        title = result.get('title', 'Untitled')
        # Try different field names for content
        content = result.get('body') or result.get('content') or result.get('text') or ''
        content = clean_content(content)
        source_type = result.get('source_type', 'unknown')
        created_at = result.get('created_at', '')[:16] if result.get('created_at') else ''
        
        # Highlight search term in content
        highlighted_content = content
        for term in query.split():
            highlighted_content = re.sub(
                f'({re.escape(term)})',
                r'<span class="highlight">\1</span>',
                highlighted_content,
                flags=re.IGNORECASE
            )
        
        # Show preview or full content (already cleaned by clean_content)
        display_content = content[:500] if len(content) > 500 else content
        if len(content) > 500:
            display_content += f'... (showing {500} of {len(content)} characters)'
        
        # For JavaScript, we need to escape quotes and newlines properly
        full_content_js = content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
        preview_js = display_content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
        
        html_content += f"""
    <div class="result">
        <div class="title">{html.escape(title)}</div>
        <div class="metadata">
            Type: {source_type} | Date: {created_at} | Length: {len(content)} chars
        </div>
        <div class="content" id="content-{i}">
            {html.escape(display_content) if display_content else '<em>No content preview available</em>'}
        </div>
        {f'<span class="expand-btn" id="btn-{i}" onclick="toggleContent({i}, &quot;{full_content_js}&quot;, &quot;{preview_js}&quot;)">Show full content</span>' if len(content) > 500 else ''}
    </div>
"""

    html_content += """
</body>
</html>
"""

    # Save to file
    output_file = Path(f"search_results_{query.replace(' ', '_')}.html")
    output_file.write_text(html_content)
    
    print(f"Results exported to: {output_file}")
    
    # Open in browser
    webbrowser.open(f"file://{output_file.absolute()}")
    
    return str(output_file)

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else input("Search query: ")
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    export_to_html(query, limit)