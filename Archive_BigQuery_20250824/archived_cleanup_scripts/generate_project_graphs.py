#!/usr/bin/env python3
"""
Comprehensive project graph generator for Email Sync Clean Backup system.
Generates multiple visualization types using current project data.
"""

import sys
import json
import sqlite3
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import networkx as nx
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def setup_output_directory():
    """Create output directory for graphs"""
    output_dir = project_root / ".cache" / "graphs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def get_database_stats():
    """Get current database statistics"""
    db_path = project_root / "data" / "system_data" / "emails.db"
    if not db_path.exists():
        return {}
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    stats = {}
    tables = [
        'content_unified', 'embeddings', 'kg_nodes', 'kg_edges', 
        'emails', 'documents', 'email_entities', 'consolidated_entities',
        'similarity_cache', 'timeline_events', 'document_summaries'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            stats[table] = count
        except sqlite3.Error:
            stats[table] = 0
    
    # Get source type breakdown
    try:
        cursor.execute("SELECT source_type, COUNT(*) FROM content_unified GROUP BY source_type")
        stats['content_by_type'] = dict(cursor.fetchall())
    except sqlite3.Error:
        stats['content_by_type'] = {}
    
    conn.close()
    return stats

def analyze_service_dependencies():
    """Analyze Python service dependencies"""
    services = {
        'Gmail': project_root / 'gmail',
        'PDF': project_root / 'pdf', 
        'Entity': project_root / 'entity',
        'Knowledge Graph': project_root / 'knowledge_graph',
        'Search Intelligence': project_root / 'search_intelligence',
        'Legal Intelligence': project_root / 'legal_intelligence',
        'Summarization': project_root / 'summarization',
        'Shared': project_root / 'shared',
        'Utilities/Embeddings': project_root / 'utilities' / 'embeddings',
        'Utilities/Vector Store': project_root / 'utilities' / 'vector_store',
        'Utilities/Timeline': project_root / 'utilities' / 'timeline',
        'Infrastructure/Pipelines': project_root / 'infrastructure' / 'pipelines',
        'Infrastructure/Documents': project_root / 'infrastructure' / 'documents',
        'Infrastructure/MCP': project_root / 'infrastructure' / 'mcp_servers'
    }
    
    dependencies = {}
    service_info = {}
    
    for service_name, service_path in services.items():
        if not service_path.exists():
            continue
            
        py_files = list(service_path.rglob('*.py'))
        total_lines = 0
        imports = set()
        
        for py_file in py_files:
            try:
                with open(py_file, encoding='utf-8') as f:
                    lines = f.readlines()
                    total_lines += len(lines)
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('from ') and not line.startswith('from .'):
                            # Extract module name
                            module = line.split('from ')[1].split(' import')[0].strip()
                            if any(svc.lower().replace('/', '.').replace(' ', '_') in module 
                                  for svc in services.keys() if svc != service_name):
                                imports.add(module)
            except Exception:
                continue
        
        service_info[service_name] = {
            'total_lines': total_lines,
            'file_count': len(py_files),
            'imports': list(imports)
        }
        dependencies[service_name] = imports
    
    return service_info, dependencies

def create_architecture_diagram(output_dir, db_stats, service_info):
    """Create high-level architecture diagram"""
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Define layer positions
    layers = {
        'Data Layer': {'y': 1.5, 'color': '#FFD700', 'height': 1.2},
        'Service Layer': {'y': 3.5, 'color': '#87CEEB', 'height': 1.8},
        'Intelligence Layer': {'y': 6.0, 'color': '#98FB98', 'height': 1.5},
        'Interface Layer': {'y': 8.2, 'color': '#DDA0DD', 'height': 1.0}
    }
    
    # Draw layers
    for layer_name, props in layers.items():
        rect = patches.Rectangle((0.5, props['y']), 9, props['height'], 
                               linewidth=2, edgecolor='black', 
                               facecolor=props['color'], alpha=0.3)
        ax.add_patch(rect)
        ax.text(0.2, props['y'] + props['height']/2, layer_name, 
               fontsize=12, fontweight='bold', rotation=90, va='center')
    
    # Data Layer components
    data_components = [
        f"SQLite Database\n({db_stats.get('content_unified', 0):,} records)",
        f"Vector Store\n({db_stats.get('embeddings', 0):,} embeddings)",
        f"Knowledge Graph\n({db_stats.get('kg_nodes', 0)} nodes, {db_stats.get('kg_edges', 0)} edges)"
    ]
    
    for i, component in enumerate(data_components):
        x = 1 + i * 2.8
        rect = patches.Rectangle((x, 1.7), 2.5, 0.8, 
                               linewidth=1, edgecolor='darkgoldenrod', 
                               facecolor='#FFFACD', alpha=0.8)
        ax.add_patch(rect)
        ax.text(x + 1.25, 2.1, component, ha='center', va='center', fontsize=9)
    
    # Service Layer components
    service_components = [
        ('Gmail\nService', service_info.get('Gmail', {}).get('total_lines', 0)),
        ('PDF\nService', service_info.get('PDF', {}).get('total_lines', 0)),
        ('Entity\nExtraction', service_info.get('Entity', {}).get('total_lines', 0)),
        ('Document\nPipeline', service_info.get('Infrastructure/Documents', {}).get('total_lines', 0))
    ]
    
    for i, (name, lines) in enumerate(service_components):
        x = 1 + i * 2.0
        rect = patches.Rectangle((x, 3.7), 1.8, 1.4, 
                               linewidth=1, edgecolor='steelblue', 
                               facecolor='#E6F3FF', alpha=0.8)
        ax.add_patch(rect)
        ax.text(x + 0.9, 4.6, name, ha='center', va='center', fontsize=9, fontweight='bold')
        ax.text(x + 0.9, 4.1, f'{lines:,} lines', ha='center', va='center', fontsize=8)
    
    # Intelligence Layer components
    intel_components = [
        ('Knowledge\nGraph', service_info.get('Knowledge Graph', {}).get('total_lines', 0)),
        ('Search\nIntelligence', service_info.get('Search Intelligence', {}).get('total_lines', 0)),
        ('Legal\nIntelligence', service_info.get('Legal Intelligence', {}).get('total_lines', 0)),
        ('Legal BERT\nEmbeddings', service_info.get('Utilities/Embeddings', {}).get('total_lines', 0))
    ]
    
    for i, (name, lines) in enumerate(intel_components):
        x = 1 + i * 2.0
        rect = patches.Rectangle((x, 6.2), 1.8, 1.1, 
                               linewidth=1, edgecolor='green', 
                               facecolor='#F0FFF0', alpha=0.8)
        ax.add_patch(rect)
        ax.text(x + 0.9, 6.9, name, ha='center', va='center', fontsize=9, fontweight='bold')
        ax.text(x + 0.9, 6.5, f'{lines:,} lines', ha='center', va='center', fontsize=8)
    
    # Interface Layer components
    interface_components = ['CLI Tools', 'MCP Servers', 'Scripts', 'Tests']
    for i, component in enumerate(interface_components):
        x = 1 + i * 2.0
        rect = patches.Rectangle((x, 8.4), 1.8, 0.6, 
                               linewidth=1, edgecolor='purple', 
                               facecolor='#F5E6FF', alpha=0.8)
        ax.add_patch(rect)
        ax.text(x + 0.9, 8.7, component, ha='center', va='center', fontsize=9)
    
    # Add title and timestamp
    ax.text(5, 9.7, 'Email Sync Clean Backup - System Architecture', 
           ha='center', va='center', fontsize=16, fontweight='bold')
    ax.text(5, 0.3, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
           ha='center', va='center', fontsize=10, style='italic')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'architecture_overview.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'architecture_overview.svg', bbox_inches='tight')
    plt.close()

def create_data_flow_diagram(output_dir, db_stats):
    """Create data flow diagram"""
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Create networkx graph for data flow
    G = nx.DiGraph()
    
    # Add nodes with data
    nodes = {
        'Gmail API': {'pos': (0, 0), 'type': 'source', 'count': db_stats.get('emails', 0)},
        'PDF Files': {'pos': (0, -2), 'type': 'source', 'count': len([x for x in db_stats.get('content_by_type', {}).keys() if 'pdf' in x.lower()])},
        'Content Unified': {'pos': (3, -1), 'type': 'storage', 'count': db_stats.get('content_unified', 0)},
        'Entity Extraction': {'pos': (6, 0), 'type': 'process', 'count': db_stats.get('email_entities', 0)},
        'Legal BERT': {'pos': (6, -2), 'type': 'process', 'count': db_stats.get('embeddings', 0)},
        'Knowledge Graph': {'pos': (9, 0), 'type': 'storage', 'count': db_stats.get('kg_edges', 0)},
        'Vector Store': {'pos': (9, -2), 'type': 'storage', 'count': db_stats.get('embeddings', 0)},
        'Search Results': {'pos': (12, -1), 'type': 'output', 'count': 0}
    }
    
    for node_id, data in nodes.items():
        G.add_node(node_id, **data)
    
    # Add edges showing data flow
    edges = [
        ('Gmail API', 'Content Unified'),
        ('PDF Files', 'Content Unified'),
        ('Content Unified', 'Entity Extraction'),
        ('Content Unified', 'Legal BERT'),
        ('Entity Extraction', 'Knowledge Graph'),
        ('Legal BERT', 'Vector Store'),
        ('Knowledge Graph', 'Search Results'),
        ('Vector Store', 'Search Results')
    ]
    
    G.add_edges_from(edges)
    
    # Draw graph
    pos = nx.get_node_attributes(G, 'pos')
    
    # Color nodes by type
    colors = {
        'source': '#FFB6C1',
        'process': '#98FB98', 
        'storage': '#87CEEB',
        'output': '#DDA0DD'
    }
    
    node_colors = [colors[G.nodes[node]['type']] for node in G.nodes()]
    
    # Draw nodes and edges
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                          node_size=3000, alpha=0.8, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color='gray', 
                          arrows=True, arrowsize=20, ax=ax)
    
    # Draw labels with counts
    labels = {}
    for node in G.nodes():
        count = G.nodes[node]['count']
        labels[node] = f"{node}\n({count:,})" if count > 0 else node
    
    nx.draw_networkx_labels(G, pos, labels, font_size=10, ax=ax)
    
    ax.set_title('Data Flow Diagram - Email Sync System', fontsize=16, fontweight='bold')
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'data_flow_diagram.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_database_schema_diagram(output_dir, db_stats):
    """Create database schema relationship diagram"""
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # Define table positions and relationships
    tables = {
        'emails': {'pos': (2, 8), 'records': db_stats.get('emails', 0), 'color': '#FFE4B5'},
        'content_unified': {'pos': (6, 8), 'records': db_stats.get('content_unified', 0), 'color': '#FFD700'},
        'documents': {'pos': (10, 8), 'records': db_stats.get('documents', 0), 'color': '#FFE4B5'},
        'embeddings': {'pos': (6, 6), 'records': db_stats.get('embeddings', 0), 'color': '#98FB98'},
        'email_entities': {'pos': (2, 6), 'records': db_stats.get('email_entities', 0), 'color': '#87CEEB'},
        'consolidated_entities': {'pos': (2, 4), 'records': db_stats.get('consolidated_entities', 0), 'color': '#87CEEB'},
        'kg_nodes': {'pos': (10, 6), 'records': db_stats.get('kg_nodes', 0), 'color': '#DDA0DD'},
        'kg_edges': {'pos': (12, 6), 'records': db_stats.get('kg_edges', 0), 'color': '#DDA0DD'},
        'similarity_cache': {'pos': (8, 6), 'records': db_stats.get('similarity_cache', 0), 'color': '#F0E68C'},
        'timeline_events': {'pos': (4, 4), 'records': db_stats.get('timeline_events', 0), 'color': '#F0E68C'},
        'document_summaries': {'pos': (8, 4), 'records': db_stats.get('document_summaries', 0), 'color': '#F0E68C'}
    }
    
    # Draw tables
    for table_name, props in tables.items():
        x, y = props['pos']
        records = props['records']
        color = props['color']
        
        # Table rectangle
        rect = patches.Rectangle((x-0.8, y-0.4), 1.6, 0.8, 
                               linewidth=1, edgecolor='black', 
                               facecolor=color, alpha=0.8)
        ax.add_patch(rect)
        
        # Table name and record count
        ax.text(x, y+0.1, table_name, ha='center', va='center', 
               fontsize=10, fontweight='bold')
        ax.text(x, y-0.2, f'{records:,} records', ha='center', va='center', 
               fontsize=8, style='italic')
    
    # Draw relationships (simplified)
    relationships = [
        ('emails', 'content_unified'),
        ('documents', 'content_unified'),
        ('content_unified', 'embeddings'),
        ('content_unified', 'email_entities'),
        ('email_entities', 'consolidated_entities'),
        ('content_unified', 'kg_nodes'),
        ('kg_nodes', 'kg_edges'),
        ('content_unified', 'similarity_cache'),
        ('content_unified', 'timeline_events'),
        ('content_unified', 'document_summaries')
    ]
    
    for source, target in relationships:
        if source in tables and target in tables:
            x1, y1 = tables[source]['pos']
            x2, y2 = tables[target]['pos']
            
            # Draw arrow
            ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                       arrowprops=dict(arrowstyle='->', color='gray', lw=1))
    
    ax.set_xlim(0, 14)
    ax.set_ylim(2, 10)
    ax.set_title('Database Schema Relationships', fontsize=16, fontweight='bold')
    ax.axis('off')
    
    # Add legend
    legend_elements = [
        patches.Patch(color='#FFE4B5', label='Source Data'),
        patches.Patch(color='#FFD700', label='Unified Content'),
        patches.Patch(color='#98FB98', label='Embeddings'),
        patches.Patch(color='#87CEEB', label='Entities'),
        patches.Patch(color='#DDA0DD', label='Knowledge Graph'),
        patches.Patch(color='#F0E68C', label='Analysis Results')
    ]
    ax.legend(handles=legend_elements, loc='lower right')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'database_schema.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_service_dependency_graph(output_dir, service_info, dependencies):
    """Create service dependency network graph"""
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Create networkx graph
    G = nx.DiGraph()
    
    # Add nodes (services)
    for service_name, info in service_info.items():
        G.add_node(service_name, lines=info['total_lines'], files=info['file_count'])
    
    # Add edges (dependencies)
    for service, deps in dependencies.items():
        for dep in deps:
            # Map dependency to service name
            for potential_service in service_info.keys():
                service_module = potential_service.lower().replace('/', '.').replace(' ', '_')
                if service_module in dep.lower():
                    G.add_edge(service, potential_service)
                    break
    
    # Layout
    pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
    
    # Node sizes based on lines of code
    node_sizes = [max(500, service_info[node]['total_lines'] / 10) for node in G.nodes()]
    
    # Node colors based on service type
    def get_node_color(service_name):
        if 'Intelligence' in service_name:
            return '#98FB98'
        elif 'Utilities' in service_name or 'Infrastructure' in service_name:
            return '#87CEEB'
        elif service_name == 'Shared':
            return '#FFD700'
        else:
            return '#FFB6C1'
    
    node_colors = [get_node_color(node) for node in G.nodes()]
    
    # Draw graph
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                          node_size=node_sizes, alpha=0.8, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color='gray', 
                          arrows=True, arrowsize=20, alpha=0.6, ax=ax)
    
    # Labels
    labels = {node: node.replace('/', '\n') for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)
    
    ax.set_title('Service Dependency Network', fontsize=16, fontweight='bold')
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'service_dependencies.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_summary_report(output_dir, db_stats, service_info):
    """Generate a comprehensive summary report"""
    report = {
        'generation_timestamp': datetime.now().isoformat(),
        'database_statistics': db_stats,
        'service_statistics': {
            name: {
                'total_lines': info['total_lines'],
                'file_count': info['file_count'],
                'import_count': len(info['imports'])
            }
            for name, info in service_info.items()
        },
        'summary': {
            'total_services': len(service_info),
            'total_lines_of_code': sum(info['total_lines'] for info in service_info.values()),
            'total_python_files': sum(info['file_count'] for info in service_info.values()),
            'total_content_records': db_stats.get('content_unified', 0),
            'total_embeddings': db_stats.get('embeddings', 0),
            'knowledge_graph_size': f"{db_stats.get('kg_nodes', 0)} nodes, {db_stats.get('kg_edges', 0)} edges"
        }
    }
    
    # Save as JSON
    with open(output_dir / 'project_analysis_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Create markdown report
    md_content = f"""# Email Sync Project Analysis Report

Generated: {report['generation_timestamp']}

## System Overview

- **Total Services**: {report['summary']['total_services']}
- **Total Lines of Code**: {report['summary']['total_lines_of_code']:,}
- **Total Python Files**: {report['summary']['total_python_files']}
- **Content Records**: {report['summary']['total_content_records']:,}
- **Vector Embeddings**: {report['summary']['total_embeddings']:,}
- **Knowledge Graph**: {report['summary']['knowledge_graph_size']}

## Database Statistics

| Table | Records |
|-------|---------|
"""
    
    for table, count in sorted(db_stats.items()):
        if isinstance(count, int):
            md_content += f"| {table} | {count:,} |\n"
    
    md_content += "\n## Service Statistics\n\n| Service | Lines | Files | Imports |\n|---------|--------|-------|---------|\n"
    
    for service, stats in sorted(report['service_statistics'].items()):
        md_content += f"| {service} | {stats['total_lines']:,} | {stats['file_count']} | {stats['import_count']} |\n"
    
    md_content += f"\n## Content Distribution\n\n"
    if 'content_by_type' in db_stats:
        for content_type, count in sorted(db_stats['content_by_type'].items()):
            md_content += f"- **{content_type}**: {count:,}\n"
    
    with open(output_dir / 'project_analysis_report.md', 'w') as f:
        f.write(md_content)
    
    return report

def main():
    """Main function to generate all graphs and reports"""
    print("Generating Email Sync project graphs and analysis...")
    
    # Setup
    output_dir = setup_output_directory()
    
    # Gather data
    print("Gathering database statistics...")
    db_stats = get_database_stats()
    
    print("Analyzing service dependencies...")
    service_info, dependencies = analyze_service_dependencies()
    
    # Generate visualizations
    print("Creating architecture diagram...")
    create_architecture_diagram(output_dir, db_stats, service_info)
    
    print("Creating data flow diagram...")
    create_data_flow_diagram(output_dir, db_stats)
    
    print("Creating database schema diagram...")
    create_database_schema_diagram(output_dir, db_stats)
    
    print("Creating service dependency graph...")
    create_service_dependency_graph(output_dir, service_info, dependencies)
    
    print("Generating summary report...")
    report = generate_summary_report(output_dir, db_stats, service_info)
    
    print(f"\nGraphs and reports generated in: {output_dir}")
    print("\nGenerated files:")
    for file_path in sorted(output_dir.iterdir()):
        print(f"  - {file_path.name}")
    
    print(f"\nProject Summary:")
    print(f"  - Services: {report['summary']['total_services']}")
    print(f"  - Lines of Code: {report['summary']['total_lines_of_code']:,}")
    print(f"  - Content Records: {report['summary']['total_content_records']:,}")
    print(f"  - Vector Embeddings: {report['summary']['total_embeddings']:,}")

if __name__ == "__main__":
    main()