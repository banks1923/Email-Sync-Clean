import argparse

def main(argv=None):
    p = argparse.ArgumentParser(description="Embedding operations")
    p.add_argument('action', choices=['build','reindex','stats'])
    args = p.parse_args(argv)
    # Placeholder wiring
    return 0

