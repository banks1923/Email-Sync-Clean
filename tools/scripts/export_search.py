#!/usr/bin/env python3
"""
Final export script with proper encoding handling
Usage: python export_search_final.py "search term" 
"""

import sys
import webbrowser
from pathlib import Path
from search_intelligence.basic_search import search as perform_search
import html
import re
from datetime import datetime

def fix_encoding(text):
    """Fix common encoding issues in text"""
    if not text:
        return ""
    
    # Common UTF-8 encoding fixes
    replacements = {
        'â€™': "'",
        'â€œ': '"',
        'â€': '"',
        'â€"': '—',
        'â€"': '–',
        'Â§': '§',
        'ï»¿': '',  # Remove BOM
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove HTML tags
    text = re.sub('<[^<]+?>', '', text)
    
    # Clean up excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def export_to_html(query, limit=20):
    results = perform_search(query, limit=limit)
    
    if not results:
        print("No results found")
        return
    
    # Process and clean results
    processed_results = []
    for result in results:
        title = fix_encoding(result.get('title', 'Untitled'))
        content = result.get('body') or result.get('content') or result.get('text') or ''
        content = fix_encoding(content)
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
    <meta charset="UTF-8">
    <title>Search Results: {html.escape(query)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .stats {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        .result {{
            background: white;
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: box-shadow 0.3s;
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
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        .content {{
            color: #333;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .preview {{
            max-height: 200px;
            overflow: hidden;
            position: relative;
        }}
        .preview::after {{
            content: "";
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 60px;
            background: linear-gradient(transparent, white);
        }}
        .expanded {{
            max-height: none;
        }}
        .expanded::after {{
            display: none;
        }}
        .expand-btn {{
            color: #1a73e8;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
            margin-top: 10px;
            display: inline-block;
            background: none;
            border: 1px solid #1a73e8;
            padding: 5px 15px;
            border-radius: 4px;
            transition: all 0.3s;
        }}
        .expand-btn:hover {{
            background: #1a73e8;
            color: white;
        }}
        .highlight {{
            background: #ffeb3b;
            padding: 2px 4px;
            border-radius: 2px;
        }}
        .char-count {{
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>Search Results: "{html.escape(query)}"</h1>
    <div class="stats">
        <strong>{len(processed_results)}</strong> results found | 
        <strong>{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</strong>
    </div>
"""

    for i, result in enumerate(processed_results):
        # Create safe version for display
        safe_content = html.escape(result['content'])
        
        # Highlight search terms (case-insensitive)
        for term in query.split():
            if term:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                safe_content = pattern.sub(
                    lambda m: f'<span class="highlight">{html.escape(m.group(0))}</span>', 
                    safe_content
                )
        
        # Determine if content needs expand button
        needs_expand = len(result['content']) > 500
        preview_class = 'preview' if needs_expand else ''
        
        html_content += f"""
    <div class="result">
        <div class="title">{html.escape(result['title'])}</div>
        <div class="metadata">
            <strong>Type:</strong> {result['source_type']} | 
            <strong>Date:</strong> {result['created_at'] or 'N/A'} | 
            <span class="char-count">{len(result['content']):,} characters</span>
        </div>
        <div class="content {preview_class}" id="content-{i}">
{safe_content}
        </div>
        {'<button class="expand-btn" onclick="toggleExpand(' + str(i) + ', this)">Show full content</button>' if needs_expand else ''}
    </div>
"""

    html_content += """
    <script>
        function toggleExpand(id, button) {
            var content = document.getElementById('content-' + id);
            if (content.classList.contains('preview')) {
                content.classList.remove('preview');
                content.classList.add('expanded');
                button.textContent = 'Show less';
            } else {
                content.classList.remove('expanded');
                content.classList.add('preview');
                button.textContent = 'Show full content';
            }
        }
    </script>
</body>
</html>
"""

    # Save to file with proper encoding
    output_file = Path(f"search_results_{query.replace(' ', '_')}.html")
    output_file.write_text(html_content, encoding='utf-8')
    
    print(f"Results exported to: {output_file}")
    
    # Open in browser
    webbrowser.open(f"file://{output_file.absolute()}")
    
    return str(output_file)

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else input("Search query: ")
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    export_to_html(query, limit)