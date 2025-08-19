#!/usr/bin/env python3
"""
Benchmark script for SimpleDB optimizations.
Compares performance with and without SQLite pragmas.
"""

import json
import os
import statistics
import tempfile
import time
from datetime import datetime
from pathlib import Path

# Temporarily disable pragmas for baseline comparison
os.environ["SIMPLEDB_CACHE_KB"] = "2000"  # Small cache for baseline

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.simple_db import SimpleDB


def bench_write(db: SimpleDB, num_docs: int = 10000) -> dict:
    """Benchmark write performance."""
    times = []
    
    # Create test table
    db.execute("""
        CREATE TABLE IF NOT EXISTS bench_test (
            id INTEGER PRIMARY KEY,
            data TEXT,
            hash TEXT UNIQUE
        )
    """)
    
    # Batch insert test documents
    for batch_start in range(0, num_docs, 100):
        batch_data = []
        for i in range(batch_start, min(batch_start + 100, num_docs)):
            data = f"Test document {i} with some content to make it realistic"
            hash_val = f"hash_{i}"
            batch_data.append((data, hash_val))
        
        t0 = time.perf_counter()
        for data, hash_val in batch_data:
            db.execute(
                "INSERT OR IGNORE INTO bench_test (data, hash) VALUES (?, ?)",
                (data, hash_val)
            )
        dt = (time.perf_counter() - t0) * 1000
        times.append(dt)
    
    return {
        "total_docs": num_docs,
        "p50_ms": round(statistics.median(times), 2),
        "p95_ms": round(statistics.quantiles(times, n=20)[18], 2) if len(times) > 20 else max(times),
        "avg_ms": round(statistics.mean(times), 2),
        "total_time_s": round(sum(times) / 1000, 2)
    }


def bench_read(db: SimpleDB, num_reads: int = 10000) -> dict:
    """Benchmark read performance."""
    times = []
    
    # Random primary key lookups
    for i in range(num_reads):
        pk = (i % 9900) + 1  # Random-ish PK within inserted range
        
        t0 = time.perf_counter()
        db.fetch_one("SELECT * FROM bench_test WHERE id = ?", (pk,))
        dt = (time.perf_counter() - t0) * 1000
        times.append(dt)
    
    return {
        "total_reads": num_reads,
        "p50_ms": round(statistics.median(times), 2),
        "p95_ms": round(statistics.quantiles(times, n=20)[18], 2) if len(times) > 20 else max(times),
        "avg_ms": round(statistics.mean(times), 2),
        "total_time_s": round(sum(times) / 1000, 2)
    }


def run_benchmark():
    """Run complete benchmark suite."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "baseline": {},
        "optimized": {}
    }
    
    print("Running SimpleDB Benchmarks...")
    print("=" * 50)
    
    # Baseline (small cache, no mmap)
    print("\n1. Baseline (2MB cache, no mmap)...")
    os.environ["SIMPLEDB_CACHE_KB"] = "2000"
    os.environ["SIMPLEDB_MMAP_BYTES"] = "0"
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        baseline_db = SimpleDB(tf.name)
        
        print("   Writing 10,000 documents...")
        results["baseline"]["write"] = bench_write(baseline_db, 10000)
        print(f"   Write p50: {results['baseline']['write']['p50_ms']}ms")
        
        print("   Reading 10,000 times...")
        results["baseline"]["read"] = bench_read(baseline_db, 10000)
        print(f"   Read p50: {results['baseline']['read']['p50_ms']}ms")
        
        # Clean up
        os.unlink(tf.name)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(tf.name + ext):
                os.unlink(tf.name + ext)
    
    # Optimized (64MB cache, 256MB mmap)
    print("\n2. Optimized (64MB cache, 256MB mmap)...")
    os.environ["SIMPLEDB_CACHE_KB"] = "64000"
    os.environ["SIMPLEDB_MMAP_BYTES"] = "268435456"
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        optimized_db = SimpleDB(tf.name)
        
        print("   Writing 10,000 documents...")
        results["optimized"]["write"] = bench_write(optimized_db, 10000)
        print(f"   Write p50: {results['optimized']['write']['p50_ms']}ms")
        
        print("   Reading 10,000 times...")
        results["optimized"]["read"] = bench_read(optimized_db, 10000)
        print(f"   Read p50: {results['optimized']['read']['p50_ms']}ms")
        
        # Report metrics
        optimized_db.metrics.report()
        
        # Clean up
        os.unlink(tf.name)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(tf.name + ext):
                os.unlink(tf.name + ext)
    
    # Calculate improvements
    write_speedup = results["baseline"]["write"]["p50_ms"] / results["optimized"]["write"]["p50_ms"]
    read_speedup = results["baseline"]["read"]["p50_ms"] / results["optimized"]["read"]["p50_ms"]
    
    results["improvements"] = {
        "write_speedup": f"{write_speedup:.1f}x",
        "read_speedup": f"{read_speedup:.1f}x"
    }
    
    # Save results
    output_file = Path(__file__).parent / "last_run.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 50)
    print("RESULTS SUMMARY:")
    print(f"Write performance: {write_speedup:.1f}x faster")
    print(f"Read performance: {read_speedup:.1f}x faster")
    print(f"\nFull results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    run_benchmark()