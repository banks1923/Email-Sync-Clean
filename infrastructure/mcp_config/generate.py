#!/usr/bin/env python3
"""MCP Configuration Generator.

PURPOSE:
--------
Generates and manages MCP (Model Context Protocol) configuration files that tell
Claude Desktop/Code which local servers to connect to for extended capabilities.

WHAT IT DOES:
- Generates .mcp.json config file for Claude to discover your MCP servers
- Validates that referenced MCP server scripts actually exist
- Shows status of current MCP configuration
- Cleans up generated config files

WHEN TO USE:
- After adding/removing MCP servers
- To validate MCP setup is working
- To regenerate configs after changes

USAGE:
  python3 -m infrastructure.mcp_config.generate status      # Check status
  python3 -m infrastructure.mcp_config.generate generate    # Create .mcp.json
  python3 -m infrastructure.mcp_config.generate validate    # Verify servers exist
  python3 -m infrastructure.mcp_config.generate clean       # Remove configs
"""

import argparse
import json
import sys
from pathlib import Path

# Handle imports for both module and script execution
try:
    # Try relative import first (when run as module)
    from .config import get_mcp_config
except ImportError:
    # Fall back to absolute import (when run as script)
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from infrastructure.mcp_config.config import get_mcp_config


def generate_mcp_json(output_path: Path | None = None, dry_run: bool = False) -> bool:
    """
    Generate .mcp.json file for Claude Code.
    
    Returns:
        bool: True if successful, False otherwise
    """
    config = get_mcp_config()
    servers = config.get_mcp_servers()

    if output_path is None:
        output_path = Path(".mcp.json")

    mcp_config = {"mcpServers": servers}

    if dry_run:
        print("📋 MCP Configuration Preview (.mcp.json):")
        print(json.dumps(mcp_config, indent=2))
        return True

    try:
        with open(output_path, "w") as f:
            json.dump(mcp_config, f, indent=2)
        print(f"✅ MCP configuration written to: {output_path}")
        return True
    except IOError as e:
        print(f"❌ Failed to write MCP configuration: {e}", file=sys.stderr)
        return False


def generate_claude_desktop_config(output_path: Path | None = None, dry_run: bool = False) -> bool:
    """
    Generate Claude Desktop configuration.
    
    Returns:
        bool: True if successful, False otherwise
    """
    config = get_mcp_config()
    servers = config.get_claude_desktop_servers()

    if output_path is None:
        # TODO: Get from config instead of hardcoding
        output_path = Path(".config/claude_desktop_config.json")

    claude_config = {"mcpServers": servers}

    if dry_run:
        print("📋 Claude Desktop Configuration Preview:")
        print(json.dumps(claude_config, indent=2))
        return True

    try:
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(claude_config, f, indent=2)
        
        print(f"✅ Claude Desktop configuration written to: {output_path}")
        return True
    except (IOError, OSError) as e:
        print(f"❌ Failed to write Claude Desktop configuration: {e}", file=sys.stderr)
        return False


def show_status() -> None:
    """
    Show MCP configuration status.
    """
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
    """
    Validate that MCP servers can be found and imported.
    """
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


def clean_configs() -> bool:
    """
    Remove generated MCP configuration files.
    
    Returns:
        bool: True if successful, False if any errors
    """
    # TODO: Get paths from config instead of hardcoding
    files_to_remove = [Path(".mcp.json"), Path(".config/claude_desktop_config.json")]

    removed_count = 0
    errors = False
    
    for file_path in files_to_remove:
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"🗑️ Removed: {file_path}")
                removed_count += 1
            except (IOError, OSError) as e:
                print(f"❌ Failed to remove {file_path}: {e}", file=sys.stderr)
                errors = True

    if removed_count == 0:
        print("ℹ️ No MCP configuration files found to remove")
    else:
        print(f"✅ Removed {removed_count} configuration file(s)")
    
    return not errors


def main():
    """
    Main CLI entry point.
    """
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
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    subparsers.add_parser("status", help="Show MCP configuration status")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate MCP configurations")
    gen_parser.add_argument(
        "--claude-desktop",
        action="store_true",
        help="Generate Claude Desktop config instead of .mcp.json",
    )
    gen_parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: .mcp.json or .config/claude_desktop_config.json)",
    )
    gen_parser.add_argument(
        "--dry-run", action="store_true", help="Preview configuration without writing files"
    )

    # Validate command
    subparsers.add_parser("validate", help="Validate MCP server files exist")

    # Clean command
    subparsers.add_parser("clean", help="Remove generated MCP configuration files")

    args = parser.parse_args()

    if args.command == "status":
        show_status()
    elif args.command == "generate":
        if args.claude_desktop:
            success = generate_claude_desktop_config(args.output, args.dry_run)
        else:
            success = generate_mcp_json(args.output, args.dry_run)
        
        if not success:
            sys.exit(1)
    
    elif args.command == "validate":
        if validate_servers():
            print("✅ All servers validated successfully")
        else:
            print("❌ Some servers failed validation")
            sys.exit(1)
    elif args.command == "clean":
        if not clean_configs():
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
