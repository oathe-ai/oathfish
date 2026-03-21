"""
Shared fixtures for Worker C verification tests.
"""
import os
import re
import pytest

# Resolve PLUGIN_ROOT to the absolute path of the oathfish project root
PLUGIN_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def parse_frontmatter(filepath):
    """Parse YAML frontmatter from a markdown file."""
    with open(filepath) as f:
        content = f.read()
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return None, content
    import yaml
    fm = yaml.safe_load(match.group(1))
    body = content[match.end():]
    return fm, body


@pytest.fixture
def plugin_root():
    return PLUGIN_ROOT
