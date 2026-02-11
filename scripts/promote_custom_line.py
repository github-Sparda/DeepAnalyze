from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.core.analytics.toolkit.custom_lines import promote_line


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a custom line into the official registry")
    parser.add_argument("--session-dir", required=True, help="Session directory containing meta/custom_lines")
    parser.add_argument("--line-id", required=True, help="Line ID to promote")
    args = parser.parse_args()

    result = promote_line(args.session_dir, args.line_id)
    print(result)


if __name__ == "__main__":
    main()
