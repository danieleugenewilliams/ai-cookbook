"""
Review the result of the legislation review results (legislation_analysis_result.json)
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import importlib.util
import sys

data = {}
file_path = Path(__file__).parent / "legislation_analysis_result.json"
if not file_path.exists():
    raise FileNotFoundError(f"Results file {file_path} does not exist.")
with open(file_path, "r") as f:
    data: List[Dict[str, Any]] = json.load(f)

if not data:
    raise ValueError("No data found in legislation_analysis_result.json")

print(f"Data: {data}")
