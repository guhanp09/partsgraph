import argparse
import json

from .pipeline import run


def main():
    parser = argparse.ArgumentParser(description="Generate and analyze the component supply scenario")
    parser.add_argument("command", choices=["run"], nargs="?", default="run")
    parser.parse_args()
    print(json.dumps(run(), indent=2))
