#!/usr/bin/env python3
"""
Documentation Truth Alignment & Drift Guard
Audits documentation claims against reality and outputs JSON report.
"""

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ServiceLineCount:
    service: str
    path: str
    exists: bool
    total_lines: int
    code_lines: int  # excluding comments and blank lines


@dataclass
class FileExistenceCheck:
    documented_path: str
    exists: bool
    actual_path: str | None = None


@dataclass
class TestPathMapping:
    documented_path: str
    exists: bool
    actual_path: str | None = None


@dataclass
class AuditReport:
    services: list[ServiceLineCount]
    missing_docs: list[FileExistenceCheck]
    test_paths: list[TestPathMapping]
    total_service_lines: int
    total_code_lines: int
    audit_timestamp: str


class DocumentationAuditor:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        
        # Define service directories to audit
        self.service_globs = {
            "gmail": "gmail/**/*.py",
            "pdf": "pdf/**/*.py", 
            "search_intelligence": "search_intelligence/**/*.py",
            "legal_intelligence": "legal_intelligence/**/*.py",
            "entity": "entity/**/*.py",
            "summarization": "summarization/**/*.py",
            "knowledge_graph": "knowledge_graph/**/*.py",
            "transcription": "transcription/**/*.py",
            "utilities/embeddings": "utilities/embeddings/**/*.py",
            "utilities/vector_store": "utilities/vector_store/**/*.py",
            "utilities/notes": "utilities/notes/**/*.py",
            "utilities/timeline": "utilities/timeline/**/*.py",
            "infrastructure/pipelines": "infrastructure/pipelines/**/*.py",
            "infrastructure/documents": "infrastructure/documents/**/*.py",
            "infrastructure/mcp_servers": "infrastructure/mcp_servers/**/*.py",
            "shared": "shared/**/*.py",
        }
        
        # Documents that should exist according to CLAUDE.md
        self.expected_docs = [
            "docs/SERVICES_API.md",
            "docs/MCP_SERVERS.md", 
            "docs/DIAGNOSTIC_SYSTEM.md",
            "docs/AUTOMATED_CLEANUP.md",
            "docs/CLEANUP_QUICK_REFERENCE.md",
            "docs/CODE_TRANSFORMATION_TOOLS.md",
        ]
        
        # Test paths mentioned in documentation
        self.expected_test_paths = [
            "tests/services/search/test_search_intelligence.py",
            "tests/services/legal/test_legal_intelligence.py",
            "tests/infrastructure/mcp/test_mcp_integration.py",
            "tests/services/knowledge_graph/test_knowledge_graph_consolidated.py",
        ]

    def count_lines_in_file(self, file_path: Path) -> tuple[int, int]:
        """Count total lines and code lines (excluding comments/blank) in a Python file."""
        try:
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            code_lines = 0
            
            for line in lines:
                stripped = line.strip()
                # Skip blank lines and comments
                if stripped and not stripped.startswith('#'):
                    code_lines += 1
                    
            return total_lines, code_lines
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
            return 0, 0

    def audit_service_lines(self) -> list[ServiceLineCount]:
        """Audit line counts for each service using glob patterns."""
        services = []
        
        for service_name, glob_pattern in self.service_globs.items():
            service_path = self.project_root / service_name.split('/')[0]
            files = list(self.project_root.glob(glob_pattern))
            
            if not files:
                services.append(ServiceLineCount(
                    service=service_name,
                    path=str(service_path),
                    exists=service_path.exists(),
                    total_lines=0,
                    code_lines=0
                ))
                continue
            
            total_lines = 0
            code_lines = 0
            
            for file_path in files:
                if file_path.is_file() and file_path.suffix == '.py':
                    file_total, file_code = self.count_lines_in_file(file_path)
                    total_lines += file_total
                    code_lines += file_code
            
            services.append(ServiceLineCount(
                service=service_name,
                path=str(service_path),
                exists=service_path.exists(),
                total_lines=total_lines,
                code_lines=code_lines
            ))
        
        return services

    def check_doc_existence(self) -> list[FileExistenceCheck]:
        """Check if documented files actually exist."""
        checks = []
        
        for doc_path in self.expected_docs:
            full_path = self.project_root / doc_path
            exists = full_path.exists()
            
            checks.append(FileExistenceCheck(
                documented_path=doc_path,
                exists=exists,
                actual_path=str(full_path) if exists else None
            ))
        
        return checks

    def check_test_paths(self) -> list[TestPathMapping]:
        """Check if documented test paths exist."""
        mappings = []
        
        for test_path in self.expected_test_paths:
            full_path = self.project_root / test_path
            exists = full_path.exists()
            
            # If exact path doesn't exist, try to find similar files
            actual_path = None
            if not exists:
                # Try to find the file in a different location
                filename = Path(test_path).name
                for found_file in self.project_root.rglob(filename):
                    if found_file.is_file():
                        actual_path = str(found_file.relative_to(self.project_root))
                        break
            else:
                actual_path = test_path
            
            mappings.append(TestPathMapping(
                documented_path=test_path,
                exists=exists,
                actual_path=actual_path
            ))
        
        return mappings

    def generate_report(self) -> AuditReport:
        """Generate complete audit report."""
        import datetime
        
        services = self.audit_service_lines()
        missing_docs = self.check_doc_existence()
        test_paths = self.check_test_paths()
        
        total_service_lines = sum(s.total_lines for s in services)
        total_code_lines = sum(s.code_lines for s in services)
        
        return AuditReport(
            services=services,
            missing_docs=missing_docs,
            test_paths=test_paths,
            total_service_lines=total_service_lines,
            total_code_lines=total_code_lines,
            audit_timestamp=datetime.datetime.now().isoformat()
        )

    def output_json(self) -> str:
        """Generate JSON audit report."""
        report = self.generate_report()
        return json.dumps(asdict(report), indent=2)

    def output_summary(self) -> str:
        """Generate human-readable summary."""
        report = self.generate_report()
        
        lines = [
            "📋 Documentation Audit Summary",
            "=" * 50,
            "",
            f"🏗️ Service Line Counts (Total: {report.total_service_lines:,} lines, Code: {report.total_code_lines:,} lines):",
        ]
        
        for service in sorted(report.services, key=lambda s: s.total_lines, reverse=True):
            status = "✅" if service.exists else "❌"
            lines.append(f"  {status} {service.service:<25} {service.total_lines:>6} lines ({service.code_lines:>6} code)")
        
        lines.extend([
            "",
            "📚 Documentation Status:",
        ])
        
        for doc in report.missing_docs:
            status = "✅" if doc.exists else "❌"
            lines.append(f"  {status} {doc.documented_path}")
        
        lines.extend([
            "",
            "🧪 Test Path Status:",
        ])
        
        for test in report.test_paths:
            if test.exists:
                lines.append(f"  ✅ {test.documented_path}")
            elif test.actual_path:
                lines.append(f"  🔄 {test.documented_path} → {test.actual_path}")
            else:
                lines.append(f"  ❌ {test.documented_path}")
        
        missing_docs = [d for d in report.missing_docs if not d.exists]
        missing_tests = [t for t in report.test_paths if not t.exists]
        
        if missing_docs or missing_tests:
            lines.extend([
                "",
                "⚠️ Issues Found:",
                f"   📚 Missing docs: {len(missing_docs)}",
                f"   🧪 Missing tests: {len(missing_tests)}",
            ])
        else:
            lines.extend([
                "",
                "✅ All documented paths exist!",
            ])
        
        return "\n".join(lines)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit documentation against reality")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--summary", action="store_true", help="Output human-readable summary")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    auditor = DocumentationAuditor(args.project_root)
    
    if args.json:
        print(auditor.output_json())
    elif args.summary:
        print(auditor.output_summary())
    else:
        # Default: JSON output for make target
        print(auditor.output_json())


if __name__ == "__main__":
    main()