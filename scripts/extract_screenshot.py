"""One-off helper: decode a base64 PNG data URL out of a saved MCP tool-result
JSON file (written when a javascript_tool result exceeds the inline token
limit) and write it to a real PNG file. Not part of the app.

Usage: python extract_screenshot.py <tool_result_json_path> <output_png_path>
"""

import base64
import json
import re
import sys

tool_result_path, output_path = sys.argv[1], sys.argv[2]

with open(tool_result_path, encoding="utf-8") as f:
    data = json.load(f)

text = data[0]["text"]
match = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", text)
if not match:
    raise SystemExit("No base64 PNG data found in tool result")

with open(output_path, "wb") as out:
    out.write(base64.b64decode(match.group(1)))

print(f"Saved {output_path} ({len(match.group(1))} base64 chars)")
