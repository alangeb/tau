#!/usr/bin/env python3
"""compress.py — Caveman text compression: drop articles, pronouns, fillers."""
import sys, re

DROP_ARTICLES = re.compile(r'\b(a|an|the)\s+', re.IGNORECASE)
DROP_PRONOUNS = re.compile(r'\b(I|you|we|they|it|he|she|me|us|them|my|your|our|their)\s+', re.IGNORECASE)
DROP_FILLERS = re.compile(r'\b(just|really|basically|actually|simply|merely|quite|very|so|then|well|now|here|there)\s+', re.IGNORECASE)
DROP_PLEASANTRIES = re.compile(r'\b(hello|hi|hey|thanks|thank you|please|sorry|apologies|indeed|certainly|of course)\b', re.IGNORECASE)
DROP_UNCERTAINTY = re.compile(r'\b(I think|it seems|note that|perhaps|maybe|possibly|I believe|in my opinion)\b', re.IGNORECASE)

def compress(text):
    """Apply caveman compression rules."""
    for pat in (DROP_ARTICLES, DROP_FILLERS, DROP_PLEASANTRIES, DROP_UNCERTAINTY, DROP_PRONOUNS):
        text = pat.sub('', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Capitalize first letter of sentences
    text = re.sub(r'(?<=\. )([a-z])', lambda m: m.group(1).upper(), text)
    if text:
        text = text[0].upper() + text[1:]
    return text

def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: compress.py [FILE] [--stdin]")
        print("  Compress text using caveman rules (drop articles, pronouns, fillers).")
        print("  FILE       Read from file")
        print("  --stdin    Read from stdin (default if no args)")
        sys.exit(0)
    if "--stdin" in sys.argv or (len(sys.argv) == 1):
        text = sys.stdin.read()
    elif len(sys.argv) == 2:
        text = open(sys.argv[1]).read()
    else:
        print("Usage: compress.py [FILE] [--stdin]", file=sys.stderr)
        sys.exit(1)
    print(compress(text))
    sys.exit(0)

if __name__ == "__main__":
    main()
