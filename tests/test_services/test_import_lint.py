import ast
import os
import pytest

def get_python_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                yield os.path.join(root, file)

class ImportVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.violations = []

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.name
            if name == 'database' or name.startswith('database.'):
                self.violations.append((node.lineno, f"Direct import of '{name}'"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module
        if module:
            if module == 'database' or module.startswith('database.'):
                self.violations.append((node.lineno, f"From-import from '{module}'"))
        self.generic_visit(node)


def test_handlers_isolation_import_lint():
    """
    [PL-6.2] [CC-1] Handlers Sterile Isolation:
    Handlers are strictly prohibited from importing database.db facade or any module under database/.
    """
    handlers_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../handlers'))
    all_violations = []

    for filepath in get_python_files(handlers_dir):
        # Пропускаем __pycache__ и т.д.
        if '__pycache__' in filepath:
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            tree = ast.parse(content, filename=filepath)
        except SyntaxError as e:
            all_violations.append((filepath, e.lineno, f"Syntax Error: {e}"))
            continue

        visitor = ImportVisitor(filepath)
        visitor.visit(tree)

        for lineno, msg in visitor.violations:
            # Относительный путь для красоты вывода
            rel_path = os.path.relpath(filepath, start=os.path.dirname(handlers_dir))
            all_violations.append(f"{rel_path}:{lineno} - {msg}")

    if all_violations:
        violations_str = "\n".join(all_violations)
        assert False, f"Import boundary violations found (handlers must NOT import from database/):\n{violations_str}"
