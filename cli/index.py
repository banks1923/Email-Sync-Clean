import argparse

def main(argv=None):
    p = argparse.ArgumentParser(description="Index operations")
    p.add_argument('action', choices=['add','reindex','prune'])
    args = p.parse_args(argv)
    # Placeholder wiring
    return 0

