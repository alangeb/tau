#!/usr/bin/env python3
"""Migrate wiki to new spec (OKF + Karpathy improvements).

Usage:
    python3 wiki_migrate.py --wiki-dir "$HOME/.local/tau/wiki" --migrate-all

Migrations:
1. Add `type` field to all frontmatter (REQUIRED by OKF)
2. Add `tags` field to all frontmatter
3. Convert relative links to absolute bundle-relative paths
4. Create log.md from existing content
5. Add # Citations sections
6. Update INDEX.md files with absolute paths
"""

import argparse
import re
import sys
from pathlib import Path


def migrate_frontmatter(content, filepath, wiki_dir):
    """Add type, tags, resource fields to frontmatter."""
    if not content.startswith('---'):
        return content

    # Extract frontmatter
    match = re.match(r'^(---\n.*?)\n---\n(.*)', content, re.DOTALL)
    if not match:
        return content

    fm_text = match.group(1)
    body = match.group(2)

    # Parse existing frontmatter
    fm_lines = fm_text.strip().split('\n')[1:]  # Skip first ---
    fm = {}
    for line in fm_lines:
        if ':' in line:
            key, _, value = line.partition(':')
            fm[key.strip()] = value.strip()

    # Add missing fields
    if 'type' not in fm:
        # Determine type from filename/content
        if 'session' in str(filepath).lower():
            fm['type'] = 'session'
        elif 'query' in str(filepath).lower():
            fm['type'] = 'query'
        else:
            fm['type'] = 'session'  # Default

    if 'tags' not in fm:
        # Extract tags from keywords or content
        keywords = fm.get('keywords', '')
        if keywords:
            fm['tags'] = '[' + keywords.replace(', ', ', ') + ']'
        else:
            fm['tags'] = '[general]'

    if 'resource' not in fm and 'source' in fm:
        # Convert source to resource (absolute path)
        source = fm['source']
        if source.startswith('../../references/'):
            fm['resource'] = '/' + source.split('/references/')[1]
        elif source.startswith('..'):
            fm['resource'] = source  # Keep as-is for now

    # Rebuild frontmatter
    new_fm = '---\n'
    for key, value in fm.items():
        new_fm += f'{key}: {value}\n'
    new_fm += '---\n'

    return new_fm + body


def convert_links(content, filepath, wiki_dir):
    """Convert relative links to absolute bundle-relative paths."""
    # Pattern: [[../../references/...|text]] or [text](../../references/...)
    def replace_link(match):
        link = match.group(0)
        # Convert ../../ to /
        link = re.sub(r'\.\./\.\./', '/', link)
        link = re.sub(r'\.\./', '/', link)
        return link

    content = re.sub(r'\[\[([^]]+)\]\]', replace_link, content)
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: f'[{m.group(1)}]({replace_link(m)})', content)

    return content


def add_citations(content, filepath, wiki_dir):
    """Add # Citations section if missing."""
    if '## Citations' in content or '# Citations' in content:
        return content

    # Find resource in frontmatter
    match = re.search(r'resource:\s*(.+)', content)
    if match:
        resource = match.group(1).strip()
        citations = f'\n## Citations\n\n[1] [Source]({resource})\n'
        # Add before last line
        lines = content.split('\n')
        if lines[-1].strip():
            content = '\n'.join(lines[:-1]) + citations + lines[-1]
        else:
            content += citations

    return content


def create_log_md(wiki_dir):
    """Create log.md from existing content."""
    log_path = wiki_dir / 'log.md'
    if log_path.exists():
        return  # Already exists

    # Scan content files for dates
    entries = []
    for md_file in wiki_dir.glob('**/*.md'):
        if md_file.name in ('INDEX.md', 'log.md'):
            continue
        try:
            content = md_file.read_text()
            match = re.search(r'updated:\s*(\d{4}-\d{2}-\d{2})', content)
            if match:
                date = match.group(1)
                title = md_file.stem
                entries.append((date, title, str(md_file.relative_to(wiki_dir))))
        except Exception:
            pass

    # Group by date
    by_date = {}
    for date, title, path in entries:
        by_date.setdefault(date, []).append((title, path))

    # Write log
    log_content = '# Wiki Log\n\n'
    for date in sorted(by_date.keys(), reverse=True):
        log_content += f'## {date}\n'
        for title, path in by_date[date]:
            log_content += f'* **Creation**: {title} ({path})\n'
        log_content += '\n'

    log_path.write_text(log_content)
    print(f'Created {log_path} with {len(entries)} entries')


def migrate_index_files(wiki_dir):
    """Update INDEX.md files with absolute paths."""
    for index_file in wiki_dir.glob('**/INDEX.md'):
        content = index_file.read_text()
        # Convert relative paths to absolute
        content = re.sub(r'`([^`]+\.\.\/[^`]+)`', lambda m: f'`/{m.group(1).replace("../", "")}`', content)
        content = re.sub(r'`([^`]+\.\.\/[^`]+)`', lambda m: f'`/{m.group(1).replace("../", "")}`', content)
        index_file.write_text(content)
        print(f'Updated {index_file}')


def main():
    parser = argparse.ArgumentParser(description='Migrate wiki to new spec')
    parser.add_argument('--wiki-dir', default='~/.local/tau/wiki', help='Wiki directory')
    parser.add_argument('--migrate-all', action='store_true', help='Run all migrations')
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir).expanduser()
    if not wiki_dir.exists():
        print(f'Wiki directory not found: {wiki_dir}')
        sys.exit(1)

    if args.migrate_all:
        print('Migrating all content files...')
        count = 0
        for md_file in wiki_dir.glob('**/*.md'):
            if md_file.name in ('INDEX.md', 'log.md'):
                continue
            content = md_file.read_text()
            content = migrate_frontmatter(content, md_file, wiki_dir)
            content = convert_links(content, md_file, wiki_dir)
            content = add_citations(content, md_file, wiki_dir)
            md_file.write_text(content)
            count += 1
            if count % 10 == 0:
                print(f'  Migrated {count} files...')

        print(f'Migrated {count} content files')

        print('Updating INDEX.md files...')
        migrate_index_files(wiki_dir)

        print('Creating log.md...')
        create_log_md(wiki_dir)

        print('Migration complete!')
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
