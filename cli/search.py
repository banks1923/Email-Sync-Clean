import argparse

def main(argv=None):
    p = argparse.ArgumentParser(description="Search operations")
    p.add_argument('query', nargs='?', help='Search query')
    p.add_argument('--limit', type=int, default=10)
    args = p.parse_args(argv)
    # Placeholder wiring; real logic lives in lib.search
    from lib import search as lib_search
    if args.query:
        results = lib_search.query(args.query, limit=args.limit)
        for r in results:
            print(r)
    else:
        p.print_help()
    return 0

