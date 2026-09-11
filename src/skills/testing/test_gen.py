#!/usr/bin/env python3
"""test_gen.py — Generate pytest test scaffold.
Usage:
  python3 skills/testing/test_gen.py <function_name> [module]
  python3 skills/testing/test_gen.py --class <class_name> [module]
  python3 skills/testing/test_gen.py --module <module>  # scan module for functions
"""
import sys
import ast
import inspect

def generate_function(func_name, module="module", return_type="None"):
    """Generate test scaffold for a function."""
    class_name = f"Test{func_name.title().replace('_', '')}"
    return f'''"""Tests for {func_name}."""
import pytest
from {module} import {func_name}

class {class_name}:
    def test_basic(self):
        """Basic functionality."""
        result = {func_name}()
        assert result is not None

    def test_edge_cases(self):
        """Edge cases."""
        # TODO: add edge case tests
        pass

    def test_error_handling(self):
        """Error handling."""
        # TODO: test error conditions
        pass

    @pytest.mark.parametrize("input_val,expected", [
        # Add test cases here
        # (input_val, expected),
    ])
    def test_parametrized(self, input_val, expected):
        """Parametrized tests."""
        assert {func_name}(input_val) == expected
'''

def generate_class(class_name, module="module"):
    """Generate test scaffold for a class."""
    return f'''"""Tests for {class_name}."""
import pytest
from {module} import {class_name}

class Test{class_name}:
    def setup_method(self):
        """Set up test fixtures."""
        self.instance = {class_name}()

    def test_init(self):
        """Test initialization."""
        assert self.instance is not None

    def test_basic(self):
        """Basic functionality."""
        # TODO: add tests
        pass

    def test_edge_cases(self):
        """Edge cases."""
        # TODO: add edge case tests
        pass
'''

def scan_module(filepath):
    """Scan a Python file for functions and classes."""
    try:
        with open(filepath) as f:
            tree = ast.parse(f.read())
        funcs = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        return funcs, classes
    except Exception as e:
        print(f"Error scanning {filepath}: {e}", file=sys.stderr)
        return [], []

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 skills/testing/test_gen.py <function_name> [module]")
        print("       python3 skills/testing/test_gen.py --class <class_name> [module]")
        print("       python3 skills/testing/test_gen.py --module <file.py>")
        sys.exit(1)

    if sys.argv[1] == "--module" and len(sys.argv) > 2:
        funcs, classes = scan_module(sys.argv[2])
        print(f"Functions: {', '.join(funcs) if funcs else '(none)'}")
        print(f"Classes: {', '.join(classes) if classes else '(none)'}")
        for func in funcs:
            print()
            print(generate_function(func, sys.argv[2].replace('.py', '').replace('/', '.')))
    elif sys.argv[1] == "--class" and len(sys.argv) > 2:
        name = sys.argv[2]
        mod = sys.argv[3] if len(sys.argv) > 3 else 'module'
        print(generate_class(name, mod))
    else:
        func = sys.argv[1]
        mod = sys.argv[2] if len(sys.argv) > 2 else 'module'
        print(generate_function(func, mod))

if __name__ == '__main__':
    main()
