"""Placeholder for multi-configuration solver comparison."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare GIS Cup solver configurations")
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.parse_args()
    raise SystemExit("Configuration comparison scaffold is ready; add experiment runner in Phase 5.")


if __name__ == "__main__":
    main()
