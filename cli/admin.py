import argparse

def main(argv=None):
    p = argparse.ArgumentParser(description="Diagnostics and info")
    p.add_argument('action', choices=['doctor','info'])
    args = p.parse_args(argv)
    # Placeholder wiring
    return 0

