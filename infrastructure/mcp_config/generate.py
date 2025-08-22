#!/usr/bin/env python3
"""
MCP Configuration Generator

CLI tool to generate MCP configurations for Claude Code and Claude Desktop.
Follows CLAUDE.md principles: Simple > Complex, Working > Perfect.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from infrastructure.mcp_config.config import get_mcp_config


def generate_mcp_json(output_path: Optional[Path] = None, dry_run: bool = False) -> None:
    """Generate .mcp.json file for Claude Code"""
    config = get_mcp_config()
    servers = config.get_mcp_servers()
    
    if output_path is None:
        output_path = Path(".mcp.json")
    
    mcp_config = {"mcpServers": servers}
    
    if dry_run:
        print("📋 MCP Configuration Preview (.mcp.json):")
        print(json.dumps(mcp_config, indent=2))
        return
    
    with open(output_path, 'w') as f:
        json.dump(mcp_config, f, indent=2)
    
    print(f"✅ MCP configuration written to: {output_path}")


def generate_claude_desktop_config(output_path: Optional[Path] = None, dry_run: bool = False) -> None:
    """Generate Claude Desktop configuration"""
    config = get_mcp_config()
    servers = config.get_claude_desktop_servers()
    
    if output_path is None:
        output_path = Path(".config/claude_desktop_config.json")
    
    claude_config = {"mcpServers": servers}
    
    if dry_run:
        print("📋 Claude Desktop Configuration Preview:")
        print(json.dumps(claude_config, indent=2))
        return
    
    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(claude_config, f, indent=2)
    
    print(f"✅ Claude Desktop configuration written to: {output_path}")


def show_status() -> None:
    """Show MCP configuration status"""
    config = get_mcp_config()
    
    print("🔧 MCP Configuration Status:")
    status = config.validate_config()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Show security warnings
    warnings = config.check_security()
    if warnings:
        print("\n🚨 Security Warnings:")
        for warning in warnings:
            print(f"  {warning}")
    
    # Show server counts
    mcp_servers = config.get_mcp_servers()
    claude_servers = config.get_claude_desktop_servers()
    print("\n📊 Server Counts:")
    print(f"  Claude Code (.mcp.json): {len(mcp_servers)} servers")
    print(f"  Claude Desktop: {len(claude_servers)} servers")


def validate_servers() -> bool:
    """Validate that MCP servers can be found and imported"""
    config = get_mcp_config()
    servers = config.get_mcp_servers()
    
    print("🔍 Validating MCP Servers:")
    all_valid = True
    
    for name, server_config in servers.items():
        if server_config.get("command") == "python3":
            # Python-based server
            script_path = server_config["args"][0]
            full_path = config.project_root / script_path
            
            if full_path.exists():
                print(f"  ✅ {name}: {script_path}")
            else:
                print(f"  ❌ {name}: {script_path} (missing)")
                all_valid = False
        elif server_config.get("command") == "npx":
            # NPM-based server
            package = server_config["args"][-1]
            print(f"  ⚠️ {name}: {package} (npm package - not validated)")
        else:
            print(f"  ❓ {name}: Unknown command type")
    
    return all_valid


def clean_configs() -> None:
    """Remove generated MCP configuration files"""
    files_to_remove = [
        Path(".mcp.json"),
        Path(".config/claude_desktop_config.json")
    ]
    
    removed_count = 0
    for file_path in files_to_remove:
        if file_path.exists():
            file_path.unlink()
            print(f"🗑️ Removed: {file_path}")
            removed_count += 1
    
    if removed_count == 0:
        print("ℹ️ No MCP configuration files found to remove")
    else:
        print(f"✅ Removed {removed_count} configuration file(s)")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Generate MCP configurations for Claude Code and Claude Desktop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate.py status                    # Show configuration status
  python generate.py generate                  # Generate .mcp.json
  python generate.py generate --claude-desktop # Generate Claude Desktop config
  python generate.py validate                  # Validate server files exist
  python generate.py clean                     # Remove generated configs
  python generate.py generate --dry-run        # Preview configuration
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show MCP configuration status')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate MCP configurations')
    gen_parser.add_argument('--claude-desktop', action='store_true',
                           help='Generate Claude Desktop config instead of .mcp.json')
    gen_parser.add_argument('--output', type=Path,
                           help='Output file path (default: .mcp.json or .config/claude_desktop_config.json)')
    gen_parser.add_argument('--dry-run', action='store_true',
                           help='Preview configuration without writing files')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate MCP server files exist')
    
    # Clean command
    subparsers.add_parser('clean', help='Remove generated MCP configuration files')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        show_status()
    elif args.command == 'generate':
        if args.claude_desktop:
            generate_claude_desktop_config(args.output, args.dry_run)
        else:
            generate_mcp_json(args.output, args.dry_run)
    elif args.command == 'validate':
        if validate_servers():
            print("✅ All servers validated successfully")
        else:
            print("❌ Some servers failed validation")
            exit(1)
    elif args.command == 'clean':
        clean_configs()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()