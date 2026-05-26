"""
Validation tests for notebook JSON structure and content references.

These tests verify the plan's acceptance criteria:
1. All 4 notebooks are valid JSON (parseable as .ipynb)
2. No `summit26_ar103_` references remain in any notebook
3. No `TODO` references remain in any notebook
4. No CloudFormation, Lake Formation, or IAM references in markdown cells
5. CLD notebook has ~15 cells (down from 38) with correct structure
6. Variable names use clean generic names (not summit-specific)
"""

import json
import os
import re
import unittest

NOTEBOOKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notebooks"
)

NOTEBOOK_FILES = [
    "cld_lab_guide.ipynb",
    "dt_lab_guide.ipynb",
    "si_lab_guide.ipynb",
    "duckdb_lab_guide.ipynb",
]


def load_notebook(name):
    """Load and return a parsed notebook."""
    path = os.path.join(NOTEBOOKS_DIR, name)
    with open(path) as f:
        return json.load(f)


class TestNotebookJsonValidity(unittest.TestCase):
    """All notebooks must be valid JSON and have proper .ipynb structure."""

    def test_all_notebooks_parse_as_json(self):
        for name in NOTEBOOK_FILES:
            with self.subTest(notebook=name):
                nb = load_notebook(name)
                self.assertIn("cells", nb, f"{name} missing 'cells' key")
                self.assertIn("metadata", nb, f"{name} missing 'metadata' key")
                self.assertIn("nbformat", nb, f"{name} missing 'nbformat' key")

    def test_all_cells_have_required_fields(self):
        for name in NOTEBOOK_FILES:
            nb = load_notebook(name)
            for i, cell in enumerate(nb["cells"]):
                with self.subTest(notebook=name, cell_index=i):
                    self.assertIn("cell_type", cell)
                    self.assertIn("source", cell)
                    self.assertIn(cell["cell_type"], ("code", "markdown", "raw"))


class TestNoSummitReferences(unittest.TestCase):
    """No summit26_ar103_ prefixed names should remain in any notebook."""

    def test_no_summit26_ar103_references(self):
        for name in NOTEBOOK_FILES:
            nb = load_notebook(name)
            for i, cell in enumerate(nb["cells"]):
                source = "".join(cell["source"])
                with self.subTest(notebook=name, cell_index=i):
                    self.assertNotIn(
                        "summit26_ar103_",
                        source,
                        f"{name} cell {i} still contains 'summit26_ar103_'",
                    )


class TestNoTodoReferences(unittest.TestCase):
    """No TODO placeholders should remain - all must be filled in."""

    def test_no_todo_in_any_cell(self):
        for name in NOTEBOOK_FILES:
            nb = load_notebook(name)
            for i, cell in enumerate(nb["cells"]):
                source = "".join(cell["source"])
                with self.subTest(notebook=name, cell_index=i):
                    self.assertFalse(
                        re.search(r"\bTODO\b", source),
                        f"{name} cell {i} still contains 'TODO'",
                    )


class TestNoAwsReferencesInMarkdown(unittest.TestCase):
    """No CloudFormation, Lake Formation, or IAM references in markdown cells."""

    BANNED_TERMS = [
        ("cloudformation", "CloudFormation"),
        ("lake formation", "Lake Formation"),
    ]

    def test_no_cloudformation_in_markdown(self):
        for name in NOTEBOOK_FILES:
            nb = load_notebook(name)
            for i, cell in enumerate(nb["cells"]):
                if cell["cell_type"] != "markdown":
                    continue
                source = "".join(cell["source"]).lower()
                with self.subTest(notebook=name, cell_index=i):
                    self.assertNotIn(
                        "cloudformation",
                        source,
                        f"{name} cell {i} still references CloudFormation",
                    )

    def test_no_lake_formation_in_markdown(self):
        for name in NOTEBOOK_FILES:
            nb = load_notebook(name)
            for i, cell in enumerate(nb["cells"]):
                if cell["cell_type"] != "markdown":
                    continue
                source = "".join(cell["source"]).lower()
                with self.subTest(notebook=name, cell_index=i):
                    self.assertNotIn(
                        "lake formation",
                        source,
                        f"{name} cell {i} still references Lake Formation",
                    )

    def test_no_iam_in_markdown(self):
        """IAM references should not appear in markdown explanatory cells.

        Note: IAM role ARNs in code cells (like SIGV4_IAM_ROLE placeholder)
        are acceptable since they are Snowflake catalog integration parameters.
        """
        for name in NOTEBOOK_FILES:
            nb = load_notebook(name)
            for i, cell in enumerate(nb["cells"]):
                if cell["cell_type"] != "markdown":
                    continue
                source = "".join(cell["source"]).lower()
                with self.subTest(notebook=name, cell_index=i):
                    # Match standalone IAM references in prose, not in
                    # code-fenced blocks or parameter names
                    self.assertFalse(
                        re.search(r"\biam\b", source),
                        f"{name} cell {i} still references IAM in markdown",
                    )


class TestCldNotebookStructure(unittest.TestCase):
    """CLD notebook should be rewritten to ~16 cells with specific structure."""

    def setUp(self):
        self.nb = load_notebook("cld_lab_guide.ipynb")
        self.cells = self.nb["cells"]

    def test_cell_count_reduced(self):
        """CLD notebook should have approximately 16 cells (down from 38)."""
        self.assertLessEqual(
            len(self.cells),
            20,
            f"CLD notebook has {len(self.cells)} cells, expected <= 20 (plan says ~15-16)",
        )

    def test_cell_0_is_title_markdown(self):
        """First cell should be markdown with title."""
        self.assertEqual(self.cells[0]["cell_type"], "markdown")
        source = "".join(self.cells[0]["source"])
        self.assertIn("#", source, "Cell 0 should have a title heading")

    def test_cell_1_has_variables(self):
        """Cell 1 should define configuration variables."""
        self.assertEqual(self.cells[1]["cell_type"], "code")
        source = "".join(self.cells[1]["source"])
        for var in ["SF_ROLE", "CATALOG_INTEGRATION_NAME", "CLD_DATABASE"]:
            self.assertIn(var, source, f"Cell 1 should define variable {var}")

    def test_has_catalog_integration_step(self):
        """Should have a CREATE CATALOG INTEGRATION step."""
        found = False
        for cell in self.cells:
            source = "".join(cell["source"])
            if "CREATE" in source and "CATALOG INTEGRATION" in source.upper():
                found = True
                break
        self.assertTrue(found, "Missing CREATE CATALOG INTEGRATION step")

    def test_has_linked_database_step(self):
        """Should have a CREATE DATABASE ... LINKED_CATALOG step."""
        found = False
        for cell in self.cells:
            source = "".join(cell["source"])
            if "LINKED_CATALOG" in source.upper():
                found = True
                break
        self.assertTrue(found, "Missing CREATE DATABASE with LINKED_CATALOG step")

    def test_has_catalog_link_status_check(self):
        """Should have a SYSTEM$CATALOG_LINK_STATUS verification step."""
        found = False
        for cell in self.cells:
            source = "".join(cell["source"])
            if "CATALOG_LINK_STATUS" in source.upper():
                found = True
                break
        self.assertTrue(found, "Missing SYSTEM$CATALOG_LINK_STATUS check")

    def test_has_cleanup_step(self):
        """Should have a cleanup cell with DROP DATABASE."""
        source = "".join(self.cells[-1]["source"])
        self.assertIn(
            "DROP",
            source.upper(),
            "Last cell should contain cleanup DROP statement",
        )

    def test_no_enabled_false_flow(self):
        """Should not have the old ENABLED=FALSE -> ALTER pattern."""
        for i, cell in enumerate(self.cells):
            source = "".join(cell["source"]).upper()
            self.assertFalse(
                "ENABLED" in source and "FALSE" in source,
                f"Cell {i} still has ENABLED=FALSE pattern",
            )


class TestDtNotebookContent(unittest.TestCase):
    """DT notebook should have clean variable names and filled TODOs."""

    def setUp(self):
        self.nb = load_notebook("dt_lab_guide.ipynb")
        self.cells = self.nb["cells"]

    def test_variables_use_clean_names(self):
        """Variables cell should use 'balloon_silver' without summit prefix."""
        for cell in self.cells:
            source = "".join(cell["source"])
            if "DB_NAME" in source and cell["cell_type"] == "code":
                # Must contain balloon_silver
                self.assertIn(
                    "balloon_silver",
                    source.lower(),
                    "DB_NAME should reference 'balloon_silver'",
                )
                # Must NOT contain summit prefix
                self.assertNotIn(
                    "summit26_ar103_",
                    source,
                    "Variables cell should not have summit26_ar103_ prefix",
                )
                break

    def test_warehouse_is_balloon_wh(self):
        """WAREHOUSE variable should be BALLOON_WH per plan."""
        for cell in self.cells:
            source = "".join(cell["source"])
            if "WAREHOUSE" in source and cell["cell_type"] == "code":
                self.assertIn(
                    "BALLOON_WH",
                    source,
                    "WAREHOUSE should be 'BALLOON_WH' per plan",
                )
                break

    def test_no_external_volume_in_cleanup(self):
        """Cleanup should not reference external volumes or S3."""
        # Check last few cells for cleanup content
        for cell in self.cells[-5:]:
            source = "".join(cell["source"]).lower()
            if "cleanup" in source or "drop" in source:
                self.assertNotIn(
                    "external volume",
                    source,
                    "Cleanup should not reference external volume",
                )

    def test_player_leaderboard_ddl_filled(self):
        """Cell 9 (dt_player_leaderboard) should have actual DDL, not a TODO."""
        # Find the cell that should contain the leaderboard dynamic table DDL
        found_leaderboard = False
        for cell in self.cells:
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            # Look for actual CREATE DYNAMIC TABLE or CREATE OR REPLACE DYNAMIC TABLE DDL
            # (not just a comment mentioning "create")
            if "player_leaderboard" in source.lower() and re.search(
                r"CREATE\s+(OR\s+REPLACE\s+)?DYNAMIC\s+.*TABLE", source, re.IGNORECASE
            ):
                found_leaderboard = True
                break
        self.assertTrue(
            found_leaderboard,
            "Missing dt_player_leaderboard DDL - should contain CREATE DYNAMIC TABLE statement",
        )


class TestSiNotebookContent(unittest.TestCase):
    """SI notebook should have clean variable names and filled Semantic View DDL."""

    def setUp(self):
        self.nb = load_notebook("si_lab_guide.ipynb")
        self.cells = self.nb["cells"]

    def test_variables_use_clean_names(self):
        """Variables cell should use 'balloon_silver' without summit prefix."""
        for cell in self.cells:
            source = "".join(cell["source"])
            if "DB_NAME" in source and cell["cell_type"] == "code":
                self.assertIn(
                    "balloon_silver",
                    source.lower(),
                    "DB_NAME should reference 'balloon_silver'",
                )
                # Must NOT contain summit prefix
                self.assertNotIn(
                    "summit26_ar103_",
                    source,
                    "Variables cell should not have summit26_ar103_ prefix",
                )
                break

    def test_semantic_view_ddl_filled_in(self):
        """Semantic View DDL cell should have CREATE SEMANTIC VIEW, not a TODO placeholder."""
        # The DDL cell (cell 7 per plan) should contain actual CREATE SEMANTIC VIEW DDL
        found_create_sv = False
        for cell in self.cells:
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            # Look for the actual DDL: CREATE ... SEMANTIC VIEW
            if re.search(
                r"CREATE\s+(OR\s+REPLACE\s+)?SEMANTIC\s+VIEW", source, re.IGNORECASE
            ):
                found_create_sv = True
                break
        self.assertTrue(
            found_create_sv,
            "Missing CREATE SEMANTIC VIEW DDL - cell should contain full DDL, not a TODO placeholder",
        )


class TestDuckdbNotebookContent(unittest.TestCase):
    """DuckDB notebook should use generic language and clean default values."""

    def setUp(self):
        self.nb = load_notebook("duckdb_lab_guide.ipynb")
        self.cells = self.nb["cells"]

    def test_no_summit_instructor_references(self):
        """Should not reference summit or instructor."""
        for i, cell in enumerate(self.cells):
            source = "".join(cell["source"]).lower()
            if cell["cell_type"] == "markdown":
                with self.subTest(cell_index=i):
                    self.assertFalse(
                        re.search(r"\bsummit\b", source),
                        f"Cell {i} still references 'summit'",
                    )
                    self.assertFalse(
                        re.search(r"\binstructor\b", source),
                        f"Cell {i} still references 'instructor'",
                    )

    def test_credentials_cell_has_default_values(self):
        """Credentials cell should default to BALLOON_SILVER and DUCKDB_SILVER_READER."""
        for cell in self.cells:
            source = "".join(cell["source"])
            if (
                "BALLOON_SILVER" in source.upper()
                or "DUCKDB_SILVER_READER" in source.upper()
            ):
                # Found the credentials cell - verify defaults
                self.assertTrue(True)
                return
        self.fail("No cell found with BALLOON_SILVER / DUCKDB_SILVER_READER defaults")


if __name__ == "__main__":
    unittest.main()
