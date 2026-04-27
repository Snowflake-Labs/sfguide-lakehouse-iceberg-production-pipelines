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
"""Glue / S3 Tables names for the bronze landing zone (single raw-events path for CLD + DT)."""

# Raw stream table: one JSON object per row in ``BRONZE_EVENT_JSON_COLUMN`` (Iceberg string).
# Snowflake DT uses ``PARSE_JSON`` / semi-structured paths. Aggregates live in Dynamic Iceberg Tables, not here.
BRONZE_RAW_EVENTS_TABLE = "balloon_game_events"
# Glue / Iceberg column holding ``FORMAT PLAIN ENCODE JSON``-shaped payload (one object per row).
BRONZE_EVENT_JSON_COLUMN = "event"

BRONZE_GLUE_TABLES: tuple[str, ...] = (BRONZE_RAW_EVENTS_TABLE,)
