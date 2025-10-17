# aicodec/infrastructure/map_generator.py
from collections.abc import Collection
from pathlib import Path


def generate_repo_map(file_paths: Collection[str]) -> str:
    """Generates a Markdown tree representation of the repository structure."""
    if not file_paths:
        return ""

    tree = {}
    relative_paths = sorted(file_paths)

    for path in relative_paths:
        parts = Path(path).parts
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = None  # Mark as a file

    def build_tree_str(node: dict, prefix: str = "") -> list[str]:
        lines = []
        entries = sorted(list(node.keys()))
        for i, name in enumerate(entries):
            is_last = i == (len(entries) - 1)
            connector = "└── " if is_last else "├── "

            is_directory = isinstance(node[name], dict)
            display_name = f"{name}/" if is_directory else name
            lines.append(f"{prefix}{connector}{display_name}")

            if is_directory:  # It's a directory
                new_prefix = prefix + ("    " if is_last else "│   ")
                lines.extend(build_tree_str(node[name], new_prefix))
        return lines

    map_lines = [".", *build_tree_str(tree)]
    return "\n".join(map_lines)
