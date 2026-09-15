"""Ensures the project root is importable when pytest is run from elsewhere."""

import sys

sys.path.insert(0, ".")
