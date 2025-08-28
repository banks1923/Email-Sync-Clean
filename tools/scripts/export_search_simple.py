#!/usr/bin/env python3
"""
Export search results to clean HTML for viewing in browser
Usage: python export_search_simple.py "search term" 
"""

import sys
import webbrowser
from pathlib import Path
from search_intelligence.basic_search import search as perform_search
import html
import re
from datetime import datetime

def clean_text(text):
    """Clean text for display"""
    # Decode HTML entities
    text = html.unescape(text)
    # Remove HTML tags
    text = re.sub('<[^<]+?>', '', text)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def export_to_html(query, limit=20):
    results = perform_search(query, limit=limit)
    
    if not results:
        print("No results found")
        return
    
    # Process results to clean content
    processed_results = []
    for result in results:
        title = result.get('title', 'Untitled')
        content = result.get('body') or result.get('content') or result.get('text') or ''
        content = clean_text(content)
        source_type = result.get('source_type', 'unknown')
        created_at = result.get('created_at', '')[:16] if result.get('created_at') else ''
        
        processed_results.append({
            'title': title,
            'content': content,
            'source_type': source_type,
            'created_at': created_at
        })
    
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
        }}
        .preview {{
            max-height: 150px;
            overflow: hidden;
            position: relative;
        }}
        .preview::after {{
            content: "";
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 50px;
            background: linear-gradient(transparent, white);
        }}
        .full {{
            max-height: none;
        }}
        .full::after {{
            display: none;
        }}
        .expand-btn {{
            color: #1a73e8;
            cursor: pointer;
            text-decoration: underline;
            font-size: 14px;
            margin-top: 10px;
            display: inline-block;
            background: none;
            border: none;
            padding: 0;
        }}
        .expand-btn:hover {{
            color: #0d47a1;
        }}
        .highlight {{
            background: yellow;
            padding: 1px 2px;
        }}
    </style>
</head>
<body>
    <h1>Search Results: "{html.escape(query)}"</h1>
    <p style="color: #666;">{len(processed_results)} results found - {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
"""

    for i, result in enumerate(processed_results):
        # Highlight search terms
        highlighted_content = result['content']
        for term in query.split():
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            highlighted_content = pattern.sub(f'<span class="highlight">{term}</span>', highlighted_content)
        
        # Determine if content needs expand button
        needs_expand = len(result['content']) > 500
        
        html_content += f"""
    <div class="result">
        <div class="title">{html.escape(result['title'])}</div>
        <div class="metadata">
            Type: {result['source_type']} | Date: {result['created_at']} | Length: {len(result['content'])} chars
        </div>
        <div class="content {'preview' if needs_expand else ''}" id="content-{i}">
            {highlighted_content}
        </div>
        {'<button class="expand-btn" onclick="toggleExpand(' + str(i) + ', this)">Show more</button>' if needs_expand else ''}
    </div>
"""

    html_content += """
    <script>
        function toggleExpand(id, button) {
            var content = document.getElementById('content-' + id);
            if (content.classList.contains('preview')) {
                content.classList.remove('preview');
                content.classList.add('full');
                button.textContent = 'Show less';
            } else {
                content.classList.remove('full');
                content.classList.add('preview');
                button.textContent = 'Show more';
            }
        }
    </script>
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