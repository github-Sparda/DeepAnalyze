#!/usr/bin/env python3
"""
Simple startup script for DeepAnalyze src/api Server
"""

import sys
import os

# Add project root to sys.path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    from main import main
    main()