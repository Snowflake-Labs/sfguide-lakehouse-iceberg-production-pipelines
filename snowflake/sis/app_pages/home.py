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

import streamlit as st

st.title("Game Analytics Dashboards")

st.markdown("""
Interactive analytics for the Balloon Popper game, powered by **Dynamic Iceberg Tables** in Snowflake.
Use the sidebar to navigate between the three dashboards.

| Dashboard | What it shows |
|---|---|
| **Leaderboard** | Top-5 scoreboard with bonus hits and score trends over time |
| **Color Analysis** | Per-player balloon color preferences, usage heatmap, and color metrics |
| **Performance Trends** | Scoring efficiency, distribution over time, and 15-second window summaries |
""")
