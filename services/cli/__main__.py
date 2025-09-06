import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(description="Litigator CLI")
    sub = parser.add_subparsers(dest='cmd', required=True)

    sub.add_parser('search', help='Search queries (semantic/hybrid)')
    sub.add_parser('embed', help='Embedding operations')
    sub.add_parser('db', help='Database admin ops')
    sub.add_parser('index', help='Indexing operations')
    sub.add_parser('admin', help='Diagnostics and info')
    sub.add_parser('view', help='Pretty view/search results')

    args, rest = parser.parse_known_args(argv)
    if args.cmd == 'search':
        from services.cli.search import main as run
    elif args.cmd == 'embed':
        from services.cli.embed import main as run
    elif args.cmd == 'db':
        from services.cli.db import main as run
    elif args.cmd == 'index':
        from services.cli.index import main as run
    elif args.cmd == 'admin':
        from services.cli.admin import main as run
    elif args.cmd == 'view':
        from services.cli.view import main as run
    else:
        parser.error('unknown command')
        return 2
    return run(rest)

if __name__ == '__main__':
    raise SystemExit(main())
