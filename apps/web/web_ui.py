#!/usr/bin/env python3
"""
Simple Web UI for Litigator Search System
Provides browser-based access to search and content viewing
"""

from flask import Flask, render_template_string, request, jsonify
from pathlib import Path
import sys
import json
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.search import search, find_literal, hybrid_search
from lib.db import SimpleDB
from lib.vector_store import get_vector_store
from lib.embeddings import get_embedding_service

app = Flask(__name__)

# HTML Template with Tailwind CSS for quick styling
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Litigator Search Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto px-4 py-8" x-data="searchApp()">
        <!-- Header -->
        <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">🔍 Litigator Search</h1>
            <div class="flex gap-4 text-sm text-gray-600">
                <span>📊 <span x-text="stats.total_docs"></span> documents</span>
                <span>🧠 <span x-text="stats.vectors"></span> vectors</span>
                <span>✅ <span x-text="stats.embeddings"></span> with embeddings</span>
                <span :class="stats.vector_status === 'healthy' ? 'text-green-600' : 'text-red-600'">
                    ⚡ Vector Store: <span x-text="stats.vector_status"></span>
                </span>
            </div>
        </div>

        <!-- Search Interface -->
        <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div class="mb-4">
                <div class="flex gap-2 mb-3">
                    <input 
                        type="text" 
                        x-model="query"
                        @keyup.enter="performSearch()"
                        placeholder="Enter search query..."
                        class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                    <select x-model="searchType" class="px-4 py-2 border border-gray-300 rounded-lg">
                        <option value="hybrid">🔎 Hybrid (RRF)</option>
                        <option value="semantic">🧠 Semantic</option>
                        <option value="literal">📝 Literal</option>
                    </select>
                    <input 
                        type="number" 
                        x-model="limit" 
                        min="1" 
                        max="50"
                        class="w-20 px-4 py-2 border border-gray-300 rounded-lg"
                    >
                    <button 
                        @click="performSearch()"
                        :disabled="searching"
                        class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
                    >
                        <span x-show="!searching">Search</span>
                        <span x-show="searching">Searching...</span>
                    </button>
                </div>
                
                <!-- Quick filters -->
                <div class="flex gap-2 text-sm">
                    <button @click="addFilter('source_type', 'email_message')" 
                            class="px-3 py-1 bg-gray-100 rounded hover:bg-gray-200">
                        📧 Emails Only
                    </button>
                    <button @click="addFilter('source_type', 'document')" 
                            class="px-3 py-1 bg-gray-100 rounded hover:bg-gray-200">
                        📄 Documents Only
                    </button>
                    <button @click="clearFilters()" 
                            class="px-3 py-1 bg-gray-100 rounded hover:bg-gray-200">
                        ❌ Clear Filters
                    </button>
                </div>
            </div>

            <!-- Active Filters -->
            <div x-show="Object.keys(filters).length > 0" class="mb-3">
                <span class="text-sm text-gray-600">Active filters:</span>
                <template x-for="[key, value] in Object.entries(filters)" :key="key">
                    <span class="inline-block px-2 py-1 ml-2 text-xs bg-blue-100 text-blue-800 rounded">
                        <span x-text="key + ': ' + value"></span>
                        <button @click="removeFilter(key)" class="ml-1">×</button>
                    </span>
                </template>
            </div>
        </div>

        <!-- Results -->
        <div x-show="results.length > 0" class="space-y-4">
            <div class="text-sm text-gray-600">
                Found <span x-text="results.length"></span> results 
                <span x-show="searchTime">(in <span x-text="searchTime"></span>ms)</span>
            </div>
            
            <template x-for="(result, index) in results" :key="result.content_id">
                <div class="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow">
                    <div class="flex justify-between items-start mb-2">
                        <div>
                            <span class="text-xs font-semibold px-2 py-1 rounded"
                                  :class="{
                                      'bg-blue-100 text-blue-800': result.source_type === 'email_message',
                                      'bg-green-100 text-green-800': result.source_type === 'document',
                                      'bg-purple-100 text-purple-800': result.source_type === 'email_summary'
                                  }">
                                <span x-text="result.source_type"></span>
                            </span>
                            <span class="ml-2 text-xs text-gray-500">
                                ID: <span x-text="result.content_id"></span>
                            </span>
                        </div>
                        <div class="text-right">
                            <div class="text-sm font-semibold text-gray-600">
                                <span x-show="result.hybrid_score">Hybrid: <span x-text="(result.hybrid_score || 0).toFixed(4)"></span></span>
                                <span x-show="!result.hybrid_score && result.semantic_score">Semantic: <span x-text="(result.semantic_score || 0).toFixed(3)"></span></span>
                            </div>
                            <div class="text-xs text-gray-500" x-show="result.vector_id">
                                Vector: <span x-text="result.vector_id"></span>
                            </div>
                        </div>
                    </div>
                    
                    <h3 class="text-lg font-semibold text-gray-800 mb-2" x-text="result.title || 'No Title'"></h3>
                    
                    <div class="text-gray-600 mb-3">
                        <div x-html="highlightContent(result.content || 'No content', query)"></div>
                    </div>
                    
                    <div class="flex gap-2 text-xs text-gray-500">
                        <span x-show="result.sender">From: <span x-text="result.sender"></span></span>
                        <span x-show="result.datetime_utc">Date: <span x-text="formatDate(result.datetime_utc)"></span></span>
                        <span>Length: <span x-text="(result.content || '').length"></span> chars</span>
                        <span x-show="result.match_sources" class="text-blue-600">
                            Sources: <span x-text="result.match_sources ? result.match_sources.join(', ') : ''"></span>
                        </span>
                    </div>
                    
                    <div class="mt-3 pt-3 border-t border-gray-200">
                        <button @click="showDetails(result)" 
                                class="text-sm text-blue-600 hover:text-blue-800">
                            View Full Details →
                        </button>
                    </div>
                </div>
            </template>
        </div>

        <!-- No Results -->
        <div x-show="searched && results.length === 0" class="bg-white rounded-lg shadow-sm p-8 text-center">
            <div class="text-gray-500">
                <div class="text-4xl mb-2">🔍</div>
                <div>No results found for "<span x-text="query"></span>"</div>
                <div class="text-sm mt-2">Try different keywords or check your filters</div>
            </div>
        </div>

        <!-- Detail Modal -->
        <div x-show="selectedItem" @click.away="selectedItem = null" 
             x-transition
             class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div class="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-auto p-6"
                 @click.stop>
                <div class="flex justify-between items-start mb-4">
                    <h2 class="text-2xl font-bold">Document Details</h2>
                    <button @click="selectedItem = null" class="text-gray-500 hover:text-gray-700">
                        ✕
                    </button>
                </div>
                
                <div x-show="selectedItem" class="space-y-4">
                    <div class="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <strong>Content ID:</strong> <span x-text="selectedItem?.content_id"></span>
                        </div>
                        <div>
                            <strong>Source ID:</strong> <span x-text="selectedItem?.source_id"></span>
                        </div>
                        <div>
                            <strong>Type:</strong> <span x-text="selectedItem?.source_type"></span>
                        </div>
                        <div>
                            <strong>Vector ID:</strong> <span x-text="selectedItem?.vector_id || 'None'"></span>
                        </div>
                    </div>
                    
                    <div>
                        <strong>Title:</strong>
                        <div class="mt-1 p-3 bg-gray-50 rounded" x-text="selectedItem?.title || 'No Title'"></div>
                    </div>
                    
                    <div>
                        <strong>Content:</strong>
                        <pre class="mt-1 p-3 bg-gray-50 rounded whitespace-pre-wrap" 
                             x-text="selectedItem?.content || 'No content'"></pre>
                    </div>
                    
                    <div x-show="selectedItem?.metadata">
                        <strong>Metadata:</strong>
                        <pre class="mt-1 p-3 bg-gray-50 rounded text-xs" 
                             x-text="JSON.stringify(selectedItem?.metadata, null, 2)"></pre>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function searchApp() {
            return {
                query: '',
                searchType: 'hybrid',
                limit: 10,
                filters: {},
                results: [],
                searching: false,
                searched: false,
                searchTime: null,
                selectedItem: null,
                stats: {
                    total_docs: 0,
                    vectors: 0,
                    embeddings: 0,
                    vector_status: 'unknown'
                },
                
                init() {
                    this.loadStats();
                },
                
                async loadStats() {
                    try {
                        const response = await fetch('/api/stats');
                        this.stats = await response.json();
                    } catch (error) {
                        console.error('Failed to load stats:', error);
                    }
                },
                
                async performSearch() {
                    if (!this.query.trim()) return;
                    
                    this.searching = true;
                    this.searched = false;
                    const startTime = Date.now();
                    
                    try {
                        const params = new URLSearchParams({
                            q: this.query,
                            type: this.searchType,
                            limit: this.limit,
                            filters: JSON.stringify(this.filters)
                        });
                        
                        const response = await fetch(`/api/search?${params}`);
                        this.results = await response.json();
                        this.searchTime = Date.now() - startTime;
                        this.searched = true;
                    } catch (error) {
                        console.error('Search failed:', error);
                        alert('Search failed: ' + error.message);
                    } finally {
                        this.searching = false;
                    }
                },
                
                highlightContent(content, query) {
                    if (!query) return this.truncateContent(content);
                    
                    const truncated = this.truncateContent(content);
                    const regex = new RegExp(`(${query})`, 'gi');
                    return truncated.replace(regex, '<mark class="bg-yellow-200">$1</mark>');
                },
                
                truncateContent(content, maxLength = 300) {
                    if (content.length <= maxLength) return content;
                    return content.substring(0, maxLength) + '...';
                },
                
                formatDate(dateStr) {
                    if (!dateStr) return '';
                    return new Date(dateStr).toLocaleDateString();
                },
                
                addFilter(key, value) {
                    this.filters[key] = value;
                    this.performSearch();
                },
                
                removeFilter(key) {
                    delete this.filters[key];
                    this.performSearch();
                },
                
                clearFilters() {
                    this.filters = {};
                    this.performSearch();
                },
                
                showDetails(item) {
                    this.selectedItem = item;
                }
            };
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main UI"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/search')
def api_search():
    """Search endpoint"""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'semantic')
    limit = int(request.args.get('limit', 10))
    filters_json = request.args.get('filters', '{}')
    
    try:
        filters = json.loads(filters_json) if filters_json else {}
    except:
        filters = {}
    
    if search_type == 'hybrid':
        results = hybrid_search(query, limit=limit, filters=filters)
    elif search_type == 'semantic':
        results = search(query, limit=limit, filters=filters)
    else:
        results = find_literal(query, limit=limit)
    
    return jsonify(results)

@app.route('/api/stats')
def api_stats():
    """Get system statistics"""
    try:
        db = SimpleDB()
        
        # Get counts
        total_docs = db.fetch_one("SELECT COUNT(*) as count FROM content_unified")['count']
        with_embeddings = db.fetch_one(
            "SELECT COUNT(*) as count FROM content_unified WHERE embedding_generated=1"
        )['count']
        
        # Get vector store status
        try:
            store = get_vector_store('vectors_v2')
            vector_count = store.count()
            health = store.health_check()
            vector_status = health['status']
        except:
            vector_count = 0
            vector_status = 'error'
        
        return jsonify({
            'total_docs': total_docs,
            'embeddings': with_embeddings,
            'vectors': vector_count,
            'vector_status': vector_status
        })
    except Exception as e:
        return jsonify({
            'total_docs': 0,
            'embeddings': 0,
            'vectors': 0,
            'vector_status': 'error',
            'error': str(e)
        })

@app.route('/api/content/<int:content_id>')
def api_content(content_id):
    """Get full content details"""
    try:
        db = SimpleDB()
        
        # Get content from database
        content = db.fetch_one(
            """SELECT * FROM content_unified WHERE id = ?""",
            (content_id,)
        )
        
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        # Get vector info if exists
        try:
            store = get_vector_store('vectors_v2')
            vector = store.get_vector(str(content_id))
            if vector:
                content['vector_info'] = {
                    'id': vector['id'],
                    'metadata': vector.get('metadata', {})
                }
        except:
            pass
        
        return jsonify(content)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Litigator Web UI")
    print("📍 Open http://localhost:5000 in your browser")
    print("Press Ctrl+C to stop")
    app.run(debug=True, port=5000)