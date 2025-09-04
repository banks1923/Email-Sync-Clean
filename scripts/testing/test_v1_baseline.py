#!/usr/bin/env python3
"""
Baseline performance test for v1 search pipeline.
Run this before v2 migration to establish performance baseline.
"""

import time
import json
from datetime import datetime
from typing import List, Dict, Any
from shared.simple_db import SimpleDB
from search_intelligence import get_search_intelligence_service

def test_search_performance(queries: List[str], limit: int = 10) -> Dict[str, Any]:
    """Test search performance with given queries."""
    service = get_search_intelligence_service()
    results = []
    
    for query in queries:
        start = time.time()
        response = service.search(query, limit=limit)
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        # Handle response as list (search returns list of results directly)
        result_count = len(response) if isinstance(response, list) else len(response.get('results', []))
        success = isinstance(response, list) or response.get('success', False)
        
        results.append({
            'query': query,
            'latency_ms': elapsed,
            'result_count': result_count,
            'success': success
        })
        
    # Calculate statistics
    latencies = [r['latency_ms'] for r in results]
    latencies.sort()
    
    stats = {
        'timestamp': datetime.now().isoformat(),
        'pipeline': 'v1',
        'queries_tested': len(queries),
        'avg_latency_ms': sum(latencies) / len(latencies),
        'p50_latency_ms': latencies[len(latencies)//2],
        'p95_latency_ms': latencies[int(len(latencies)*0.95)] if len(latencies) > 1 else latencies[0],
        'max_latency_ms': max(latencies),
        'min_latency_ms': min(latencies),
        'individual_results': results
    }
    
    return stats

def test_database_performance() -> Dict[str, Any]:
    """Test database query performance."""
    db = SimpleDB()
    
    # Test content counts
    start = time.time()
    cursor = db.execute("""
        SELECT COUNT(*) as total,
               SUM(ready_for_embedding) as ready,
               SUM(embedding_generated) as embedded
        FROM content_unified
    """)
    count_result = cursor.fetchone()
    count_time = (time.time() - start) * 1000
    
    # Test search query
    start = time.time()
    cursor = db.execute("""
        SELECT id, title, substr(body, 1, 100) as snippet
        FROM content_unified
        WHERE body LIKE ?
        LIMIT 10
    """, ('%lease%',))
    search_results = cursor.fetchall()
    search_time = (time.time() - start) * 1000
    
    return {
        'content_stats': {
            'total': count_result['total'],
            'ready_for_embedding': count_result['ready'],
            'already_embedded': count_result['embedded']
        },
        'count_query_ms': count_time,
        'search_query_ms': search_time,
        'search_result_count': len(search_results)
    }

def main():
    """Run baseline performance tests."""
    print("Running v1 Baseline Performance Tests")
    print("=" * 50)
    
    # Define test queries
    test_queries = [
        "lease",
        "tenant rights",
        "eviction notice",
        "security deposit",
        "habitability",
        "rent control",
        "mold inspection",
        "breach of contract",
        "discrimination",
        "retaliation"
    ]
    
    # Test search performance
    print("\nTesting search performance...")
    search_stats = test_search_performance(test_queries)
    
    print(f"✅ Tested {search_stats['queries_tested']} queries")
    print(f"   Avg latency: {search_stats['avg_latency_ms']:.2f}ms")
    print(f"   P50 latency: {search_stats['p50_latency_ms']:.2f}ms")
    print(f"   P95 latency: {search_stats['p95_latency_ms']:.2f}ms")
    
    # Test database performance
    print("\nTesting database performance...")
    db_stats = test_database_performance()
    
    print("✅ Database stats:")
    print(f"   Total content: {db_stats['content_stats']['total']}")
    print(f"   Ready for embedding: {db_stats['content_stats']['ready_for_embedding']}")
    print(f"   Already embedded: {db_stats['content_stats']['already_embedded']}")
    print(f"   Count query: {db_stats['count_query_ms']:.2f}ms")
    print(f"   Search query: {db_stats['search_query_ms']:.2f}ms")
    
    # Save results
    baseline = {
        'search_performance': search_stats,
        'database_performance': db_stats
    }
    
    output_file = f"baseline_v1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(baseline, f, indent=2)
    
    print(f"\n✅ Baseline saved to {output_file}")
    
    # Check if performance meets requirements
    if search_stats['p95_latency_ms'] < 200:
        print("✅ P95 latency < 200ms requirement: PASSED")
    else:
        print(f"⚠️  P95 latency < 200ms requirement: FAILED ({search_stats['p95_latency_ms']:.2f}ms)")

if __name__ == "__main__":
    main()