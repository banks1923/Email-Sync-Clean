#!/usr/bin/env python3
"""
System Health Check Graph Generator
Generates comprehensive health visualizations for the Email Sync System
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

def get_db_path():
    """Get database path consistently"""
    return Path(__file__).parent.parent / "data" / "system_data" / "emails.db"

def get_database_stats():
    """Get comprehensive database statistics"""
    db_path = get_db_path()
    if not db_path.exists():
        return None
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    stats = {}
    
    # Get table counts
    tables = [
        'content_unified', 'individual_messages', 'documents', 
        'embeddings', 'consolidated_entities', 'timeline_events',
        'processing_errors'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            stats[table] = 0
    
    # Get database size
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    stats['db_size_mb'] = (page_size * page_count) / (1024 * 1024)
    
    # Get processing statistics
    try:
        cursor.execute("""
            SELECT source_type, validation_status, COUNT(*) 
            FROM content_unified 
            GROUP BY source_type, validation_status
        """)
        stats['content_by_type'] = cursor.fetchall()
    except sqlite3.OperationalError:
        stats['content_by_type'] = []
    
    conn.close()
    return stats

def get_file_system_stats():
    """Get file system statistics"""
    base_path = Path(__file__).parent.parent / "data"
    stats = {}
    
    # Count files in different directories
    directories = {
        'user_data': base_path / "Stoneman_dispute" / "user_data",
        'system_data': base_path / "system_data",
        'backups': base_path / "system_data" / "backups",
        'cache': base_path / "system_data" / "cache",
        'quarantine': base_path / "system_data" / "quarantine"
    }
    
    for name, path in directories.items():
        if path.exists():
            files = list(path.rglob('*'))
            stats[f'{name}_files'] = len([f for f in files if f.is_file()])
            stats[f'{name}_size_mb'] = sum(f.stat().st_size for f in files if f.is_file()) / (1024 * 1024)
        else:
            stats[f'{name}_files'] = 0
            stats[f'{name}_size_mb'] = 0.0
    
    return stats

def check_services_status():
    """Check status of key services"""
    status = {}
    
    # Check Qdrant connection
    try:
        import requests
        response = requests.get('http://localhost:6333/health', timeout=2)
        status['qdrant'] = 'healthy' if response.status_code == 200 else 'unhealthy'
    except:
        status['qdrant'] = 'offline'
    
    # Check database accessibility
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path), timeout=1)
        conn.execute("SELECT 1")
        conn.close()
        status['database'] = 'healthy'
    except:
        status['database'] = 'unhealthy'
    
    # Check critical directories
    base_path = Path(__file__).parent.parent / "data"
    status['file_system'] = 'healthy' if base_path.exists() else 'unhealthy'
    
    return status

def create_system_health_dashboard():
    """Create comprehensive system health dashboard"""
    
    # Get all statistics
    db_stats = get_database_stats() or {}
    fs_stats = get_file_system_stats()
    service_status = check_services_status()
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('Email Sync System - Health Dashboard', fontsize=20, fontweight='bold')
    
    # Color scheme
    colors = {
        'healthy': '#2ecc71',
        'warning': '#f39c12', 
        'unhealthy': '#e74c3c',
        'offline': '#95a5a6',
        'primary': '#3498db'
    }
    
    # 1. Service Status (top left)
    ax1 = plt.subplot(2, 3, 1)
    services = ['Qdrant', 'Database', 'File System']
    statuses = [service_status.get('qdrant', 'offline'), 
               service_status.get('database', 'unhealthy'),
               service_status.get('file_system', 'unhealthy')]
    
    status_colors = [colors.get(status, colors['offline']) for status in statuses]
    
    bars1 = ax1.barh(services, [1, 1, 1], color=status_colors, alpha=0.8)
    ax1.set_xlim(0, 1)
    ax1.set_title('Service Status', fontweight='bold', fontsize=14)
    ax1.set_xticks([])
    
    # Add status text on bars
    for i, (bar, status) in enumerate(zip(bars1, statuses)):
        ax1.text(0.5, i, status.upper(), ha='center', va='center', 
                fontweight='bold', color='white')
    
    # 2. Database Statistics (top middle)
    ax2 = plt.subplot(2, 3, 2)
    
    if db_stats:
        tables = ['content_unified', 'documents', 'embeddings', 'consolidated_entities']
        counts = [db_stats.get(table, 0) for table in tables]
        table_labels = ['Content\nUnified', 'Documents', 'Embeddings', 'Entities']
        
        bars2 = ax2.bar(table_labels, counts, color=colors['primary'], alpha=0.7)
        ax2.set_title('Database Record Counts', fontweight='bold', fontsize=14)
        ax2.set_ylabel('Count')
        
        # Add value labels on bars
        for bar, count in zip(bars2, counts):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + max(counts)*0.01,
                    f'{count:,}', ha='center', va='bottom', fontweight='bold')
    else:
        ax2.text(0.5, 0.5, 'Database\nUnavailable', ha='center', va='center', 
                transform=ax2.transAxes, fontsize=16, color=colors['unhealthy'])
        ax2.set_title('Database Record Counts', fontweight='bold', fontsize=14)
    
    # 3. Storage Usage (top right)
    ax3 = plt.subplot(2, 3, 3)
    
    storage_categories = ['User Data', 'System Data', 'Backups', 'Cache']
    storage_sizes = [
        fs_stats.get('user_data_size_mb', 0),
        fs_stats.get('system_data_size_mb', 0),
        fs_stats.get('backups_size_mb', 0),
        fs_stats.get('cache_size_mb', 0)
    ]
    
    # Create pie chart for storage
    non_zero_sizes = [(cat, size) for cat, size in zip(storage_categories, storage_sizes) if size > 0]
    if non_zero_sizes:
        labels, sizes = zip(*non_zero_sizes)
        ax3.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    else:
        ax3.text(0.5, 0.5, 'No Storage\nData Available', ha='center', va='center',
                transform=ax3.transAxes, fontsize=12)
    
    ax3.set_title('Storage Usage Distribution', fontweight='bold', fontsize=14)
    
    # 4. File Counts (bottom left)
    ax4 = plt.subplot(2, 3, 4)
    
    file_categories = ['User Files', 'System Files', 'Backups', 'Quarantine']
    file_counts = [
        fs_stats.get('user_data_files', 0),
        fs_stats.get('system_data_files', 0),
        fs_stats.get('backups_files', 0),
        fs_stats.get('quarantine_files', 0)
    ]
    
    bars4 = ax4.bar(file_categories, file_counts, color=colors['primary'], alpha=0.6)
    ax4.set_title('File Count Distribution', fontweight='bold', fontsize=14)
    ax4.set_ylabel('File Count')
    plt.setp(ax4.get_xticklabels(), rotation=45, ha='right')
    
    # Add value labels
    for bar, count in zip(bars4, file_counts):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + max(file_counts)*0.01,
                f'{count}', ha='center', va='bottom', fontweight='bold')
    
    # 5. Content Processing Status (bottom middle)
    ax5 = plt.subplot(2, 3, 5)
    
    if db_stats and db_stats.get('content_by_type'):
        # Process content by type data
        content_data = {}
        for source_type, validation_status, count in db_stats['content_by_type']:
            if source_type not in content_data:
                content_data[source_type] = {}
            content_data[source_type][validation_status] = count
        
        if content_data:
            # Create stacked bar chart
            source_types = list(content_data.keys())
            validated_counts = [content_data[st].get('validated', 0) for st in source_types]
            pending_counts = [content_data[st].get('pending', 0) for st in source_types]
            failed_counts = [content_data[st].get('failed', 0) for st in source_types]
            
            width = 0.6
            ax5.bar(source_types, validated_counts, width, label='Validated', 
                   color=colors['healthy'], alpha=0.8)
            ax5.bar(source_types, pending_counts, width, bottom=validated_counts, 
                   label='Pending', color=colors['warning'], alpha=0.8)
            ax5.bar(source_types, failed_counts, width, 
                   bottom=[v+p for v,p in zip(validated_counts, pending_counts)],
                   label='Failed', color=colors['unhealthy'], alpha=0.8)
            
            ax5.legend()
        else:
            ax5.text(0.5, 0.5, 'No Content\nProcessing Data', ha='center', va='center',
                    transform=ax5.transAxes, fontsize=12)
    else:
        ax5.text(0.5, 0.5, 'Content Processing\nData Unavailable', ha='center', va='center',
                transform=ax5.transAxes, fontsize=12)
    
    ax5.set_title('Content Processing Status', fontweight='bold', fontsize=14)
    ax5.set_ylabel('Count')
    plt.setp(ax5.get_xticklabels(), rotation=45, ha='right')
    
    # 6. System Summary (bottom right)
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    
    # Create summary text
    summary_text = []
    summary_text.append("SYSTEM SUMMARY")
    summary_text.append("=" * 15)
    summary_text.append("")
    
    # Service status summary
    healthy_services = sum(1 for status in service_status.values() if status == 'healthy')
    total_services = len(service_status)
    summary_text.append(f"Services: {healthy_services}/{total_services} Healthy")
    
    # Database summary
    if db_stats:
        total_records = sum(db_stats.get(table, 0) for table in ['content_unified', 'documents', 'embeddings'])
        summary_text.append(f"Database: {total_records:,} records")
        summary_text.append(f"DB Size: {db_stats.get('db_size_mb', 0):.1f} MB")
    else:
        summary_text.append("Database: Unavailable")
    
    # File system summary  
    total_files = sum(fs_stats.get(f'{cat}_files', 0) for cat in ['user_data', 'system_data', 'backups'])
    total_storage = sum(fs_stats.get(f'{cat}_size_mb', 0) for cat in ['user_data', 'system_data', 'backups'])
    summary_text.append(f"Files: {total_files} total")
    summary_text.append(f"Storage: {total_storage:.1f} MB")
    
    summary_text.append("")
    summary_text.append(f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    ax6.text(0.05, 0.95, '\n'.join(summary_text), transform=ax6.transAxes, 
            fontsize=11, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgray', alpha=0.8))
    
    # Overall health status indicator
    overall_health = 'healthy' if healthy_services == total_services and db_stats else 'warning'
    health_color = colors.get(overall_health, colors['unhealthy'])
    
    ax6.text(0.05, 0.05, f"Overall Status: {overall_health.upper()}", 
            transform=ax6.transAxes, fontsize=14, fontweight='bold',
            color=health_color, verticalalignment='bottom')
    
    plt.tight_layout()
    return fig

def main():
    """Main function to generate and save health dashboard"""
    
    # Create the dashboard
    fig = create_system_health_dashboard()
    
    # Save to file
    output_dir = Path(__file__).parent.parent / "data" / "system_data"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"system_health_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    fig.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    
    print(f"System health dashboard saved to: {output_file}")
    
    # Also save as latest
    latest_file = output_dir / "system_health_dashboard_latest.png"
    fig.savefig(latest_file, dpi=300, bbox_inches='tight', facecolor='white')
    
    print(f"Latest dashboard saved to: {latest_file}")
    
    # Show the plot
    plt.show()
    
    return str(output_file)

if __name__ == "__main__":
    main()