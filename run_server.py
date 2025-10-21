#!/usr/bin/env python3
"""
Main runner for the SAP Tools FastAPI server.
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.main import main
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

# Run the main function from main.py
if __name__ == "__main__":
    main()
