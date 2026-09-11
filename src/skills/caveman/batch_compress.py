#!/usr/bin/env python3
"""batch_compress.py — Compress multiple files to caveman style.
Usage: python3 skills/caveman/batch_compress.py <file1> [file2 ...] [--dry-run]
Removes articles, fillers, pleasantries. Preserves code blocks.
"""
import sys, re, os

# Patterns to remove/replace
ARTICLES = re.compile(r'\b(a|an|the)\b', re.IGNORECASE)
FILLERS = re.compile(r'\b(just|really|basically|simply|actually|essentially|generally|typically)\b', re.IGNORECASE)
PLEASANTRIES = re.compile(r'\b(here (is|are)|please|thank you|note that|remember to|don\'t forget)\b', re.IGNORECASE)

def compress(text):
    """Compress text to caveman style."""
    lines = text.split('\n')
    result = []
    in_code = False
    
    for line in lines:
        # Track code blocks
        if line.strip().startswith('```'):
            in_code = not in_code
            result.append(line)
            continue
        
        if in_code:
            result.append(line)
            continue
        
        # Compress non-code lines
        compressed = line
        compressed = ARTICLES.sub('', compressed)
        compressed = FILLERS.sub('', compressed)
        compressed = PLEASANTRIES.sub('', compressed)
        # Clean up double spaces
        compressed = re.sub(r'  +', ' ', compressed)
        # Capitalize after periods
        compressed = re.sub(r'(\.)(\s+)([a-z])', lambda m: m.group(1) + m.group(2) + m.group(3).upper(), compressed)
        result.append(compressed.strip())
    
    return '\n'.join(result)

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 skills/caveman/batch_compress.py <files...> [--dry-run]")
        sys.exit(1)
    
    dry_run = '--dry-run' in args
    files = [a for a in args if not a.startswith('--')]
    
    for fpath in files:
        if not os.path.exists(fpath):
            print(f"SKIP: {fpath} (not found)")
            continue
        
        original = open(fpath).read()
        compressed = compress(original)
        
        if compressed == original:
            print(f"OK: {fpath} (already compressed)")
            continue
        
        if dry_run:
            print(f"WOULD CHANGE: {fpath}")
            # Show first diff
            orig_lines = original.split('\n')
            comp_lines = compressed.split('\n')
            for i, (o, c) in enumerate(zip(orig_lines, comp_lines)):
                if o != c:
                    print(f"  Line {i+1}: {o[:60]}")
                    print(f"           → {c[:60]}")
                    break
        else:
            open(fpath, 'w').write(compressed)
            print(f"COMPRESSED: {fpath}")

if __name__ == '__main__':
    main()
