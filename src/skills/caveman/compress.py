#!/usr/bin/env python3
"""caveman_compress.py — Text compression helper."""
import re

def compress_text(text: str) -> str:
    """Compress text using caveman style rules."""
    # Remove articles
    text = re.sub(r'\b(a|an|the)\s+', '', text, flags=re.IGNORECASE)
    # Remove fillers
    text = re.sub(r'\b(just|really|basically|actually|simply|merely|quite|very)\s+', '', text, flags=re.IGNORECASE)
    # Remove pleasantries
    text = re.sub(r'\b(hello|hi|hey|thanks|thank you|please|sorry|apologies|indeed)\b', '', text, flags=re.IGNORECASE)
    # Remove uncertainty markers
    text = re.sub(r'\b(I think|it seems|note that|perhaps|maybe|possibly|I believe)\b', '', text, flags=re.IGNORECASE)
    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def compress_file(input_path: str, output_path: str = None) -> str:
    """Compress a text file."""
    with open(input_path) as f:
        text = f.read()
    result = compress_text(text)
    if output_path:
        with open(output_path, 'w') as f:
            f.write(result)
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: caveman_compress.py <input_file> [output_file]")
        sys.exit(1)
    result = compress_file(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    if len(sys.argv) > 2:
        print(f"Compressed to {sys.argv[2]}")
    else:
        print(result)
