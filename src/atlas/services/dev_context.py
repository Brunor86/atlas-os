from __future__ import annotations

import ast
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


class DevContextService:
    """Build a compact architectural context and audit for ATLAS development."""

    ROOT = Path(__file__).resolve().parents[3]
    SRC = ROOT / "src" / "atlas"

    def build(self) -> dict:
        files = self._python_files()

        return {
            "git": self._git_context(),
            "architecture": self._architecture(files),
            "symbols": self._symbols(files),
            "duplicates": self._duplicates(files),
            "imports": self._imports(files),
            "risk": self._risk(files),
            "recent_commits": self._recent_commits(),
        }

    # ------------------------------------------------------------------
    # FILE DISCOVERY
    # ------------------------------------------------------------------

    def _python_files(self) -> list[Path]:
        if not self.SRC.exists():
            return []

        return sorted(
            path
            for path in self.SRC.rglob("*.py")
            if "__pycache__" not in path.parts
        )

    # ------------------------------------------------------------------
    # GIT
    # ------------------------------------------------------------------

    def _git(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.stdout.strip()

        except Exception:
            return ""

    def _git_context(self) -> dict:
        branch = self._git("branch", "--show-current")
        commit = self._git("rev-parse", "--short", "HEAD")

        tag = self._git(
            "describe",
            "--tags",
            "--exact-match",
            "HEAD",
        )

        status = self._git("status", "--short")

        return {
            "branch": branch,
            "commit": commit,
            "tag": tag or "untagged",
            "dirty": bool(status),
            "dirty_files": (
                len(status.splitlines())
                if status
                else 0
            ),
        }

    def _recent_commits(self) -> list[str]:
        output = self._git(
            "log",
            "--oneline",
            "--decorate",
            "-8",
        )

        return output.splitlines() if output else []

    # ------------------------------------------------------------------
    # ARCHITECTURE
    # ------------------------------------------------------------------

    def _architecture(
        self,
        files: list[Path],
    ) -> dict:

        tree = defaultdict(list)

        for path in files:
            relative = path.relative_to(self.SRC)

            if len(relative.parts) == 1:
                key = "."
            else:
                key = relative.parts[0]

            tree[key].append(str(relative))

        return {
            key: {
                "count": len(value),
                "files": value,
            }
            for key, value in sorted(tree.items())
        }

    # ------------------------------------------------------------------
    # AST SYMBOLS
    # ------------------------------------------------------------------

    def _parse(self, path: Path):
        try:
            return ast.parse(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            SyntaxError,
            UnicodeDecodeError,
        ):
            return None

    def _symbols(
        self,
        files: list[Path],
    ) -> dict:

        classes = []
        functions = []

        for path in files:
            tree = self._parse(path)

            if tree is None:
                continue

            relative = str(
                path.relative_to(self.ROOT)
            )

            for node in ast.walk(tree):

                if isinstance(node, ast.ClassDef):
                    classes.append(
                        {
                            "name": node.name,
                            "file": relative,
                            "line": node.lineno,
                            "methods": [
                                child.name
                                for child in node.body
                                if isinstance(
                                    child,
                                    (
                                        ast.FunctionDef,
                                        ast.AsyncFunctionDef,
                                    ),
                                )
                            ],
                        }
                    )

                elif isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):
                    functions.append(
                        {
                            "name": node.name,
                            "file": relative,
                            "line": node.lineno,
                        }
                    )

        return {
            "python_files": len(files),
            "class_count": len(classes),
            "function_count": len(functions),
            "classes": classes,
            "functions": functions,
        }

    # ------------------------------------------------------------------
    # DUPLICATION ANALYSIS
    # ------------------------------------------------------------------

    def _duplicates(
        self,
        files: list[Path],
    ) -> dict:

        class_map = defaultdict(list)
        function_map = defaultdict(list)

        for path in files:
            tree = self._parse(path)

            if tree is None:
                continue

            relative = str(
                path.relative_to(self.ROOT)
            )

            for node in tree.body:

                if isinstance(node, ast.ClassDef):
                    class_map[node.name].append(
                        {
                            "file": relative,
                            "line": node.lineno,
                        }
                    )

                elif isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):
                    function_map[node.name].append(
                        {
                            "file": relative,
                            "line": node.lineno,
                        }
                    )

        duplicate_classes = {
            name: entries
            for name, entries in class_map.items()
            if len(entries) > 1
        }

        duplicate_functions = {
            name: entries
            for name, entries in function_map.items()
            if len(entries) > 1
        }

        return {
            "duplicate_classes": duplicate_classes,
            "duplicate_functions": duplicate_functions,
        }

    # ------------------------------------------------------------------
    # IMPORT GRAPH
    # ------------------------------------------------------------------

    def _imports(
        self,
        files: list[Path],
    ) -> dict:

        imports = defaultdict(set)

        for path in files:
            tree = self._parse(path)

            if tree is None:
                continue

            relative = str(
                path.relative_to(self.ROOT)
            )

            for node in ast.walk(tree):

                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports[relative].add(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports[relative].add(node.module)

        return {
            file: sorted(values)
            for file, values in sorted(imports.items())
        }

    # ------------------------------------------------------------------
    # RISK / ARCHITECTURAL HOTSPOTS
    # ------------------------------------------------------------------

    def _risk(
        self,
        files: list[Path],
    ) -> dict:

        service_files = [
            path
            for path in files
            if "services" in path.parts
        ]

        model_files = [
            path
            for path in files
            if "models" in path.parts
        ]

        service_names = Counter(
            path.stem
            for path in service_files
        )

        model_names = Counter(
            path.stem
            for path in model_files
        )

        duplicate_service_names = {
            name: count
            for name, count in service_names.items()
            if count > 1
        }

        duplicate_model_names = {
            name: count
            for name, count in model_names.items()
            if count > 1
        }

        return {
            "service_files": len(service_files),
            "model_files": len(model_files),
            "duplicate_service_names": duplicate_service_names,
            "duplicate_model_names": duplicate_model_names,
        }
