"""Architecture guard for the Streamlit presentation layer."""

import ast
from pathlib import Path


def test_ui_does_not_import_aws_or_repository_adapters() -> None:
    source = Path("app/ui.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert "boto3" not in imported_modules
    assert not any(module.startswith("app.repositories") for module in imported_modules)
    assert not any(
        module.startswith("app.language_models") for module in imported_modules
    )


def test_ui_routes_case_chat_through_the_agentcore_client() -> None:
    source = Path("app/ui.py").read_text(encoding="utf-8")

    assert "create_agentcore_runtime_client" in source
    assert "create_grounded_case_agent" not in source
