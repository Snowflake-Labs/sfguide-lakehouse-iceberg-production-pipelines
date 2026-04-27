# Copyright 2025 Snowflake Inc.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Single place for Snowflake lab defaults (CLD chapter + tasks)."""

import os

# Matches examples in lab/snowflake-catalog-cld.md and generated SQL comments.
DEFAULT_CATALOG_INTEGRATION_NAME = "glue_rest_catalog_int"

# Solo-lab default IAM role name for Snowflake Glue REST SIGV4 (`create-read-role` when LAB_USERNAME unset).
# With LAB_USERNAME, the CLI derives ``<glue_slug>_snowflake_glue_catalog_read`` (see bronze_aws).
DEFAULT_GLUE_CATALOG_READ_ROLE_NAME = "snowflake_glue_catalog_read"

# Dynamic Iceberg Tables chapter (silver) — native DB/schema for Snowflake-managed Iceberg outputs.
DEFAULT_SILVER_DATABASE = "balloon_silver"
DEFAULT_SILVER_SCHEMA = "silver"
# Warehouse for DT refresh (override with SNOWFLAKE_WAREHOUSE).
DEFAULT_SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"


def resolve_catalog_integration_name() -> str:
    """Return catalog integration name honoring LAB_USERNAME workshop prefix.

    Precedence: ``SNOWFLAKE_CATALOG_INTEGRATION_NAME`` env var →
    ``<glue_slug>_glue_rest_catalog_int`` (when ``LAB_USERNAME`` is set) →
    :data:`DEFAULT_CATALOG_INTEGRATION_NAME`.

    Mirrors the slug logic used for IAM role names
    (``<glue_slug>_snowflake_glue_catalog_read``) so all workshop resources
    share a consistent per-participant prefix.
    """
    explicit = (os.environ.get("SNOWFLAKE_CATALOG_INTEGRATION_NAME") or "").strip()
    if explicit:
        return explicit
    lab = (os.environ.get("LAB_USERNAME") or "").strip()
    if lab:
        from tools.bronze_preload.bronze_aws import sanitize_lab_slug_glue

        slug = sanitize_lab_slug_glue(lab)
        if slug:
            return f"{slug}_{DEFAULT_CATALOG_INTEGRATION_NAME}"
    return DEFAULT_CATALOG_INTEGRATION_NAME
