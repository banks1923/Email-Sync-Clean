import argparse

def main(argv=None):
    p = argparse.ArgumentParser(description="Database admin")
    p.add_argument('action', choices=['migrate','backup','restore','vacuum'])
    args = p.parse_args(argv)
    # Placeholder wiring
    return 0

