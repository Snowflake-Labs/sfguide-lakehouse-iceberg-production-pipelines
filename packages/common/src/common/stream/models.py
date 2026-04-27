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

import os
from datetime import datetime, timezone

from pydantic import BaseModel


class GameEvent(BaseModel):
    player: str
    balloon_color: str
    score: int
    favorite_color_bonus: bool
    event_ts: str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class PlayerScore(BaseModel):
    player: str
    total_score: int = 0
    bonus_hits: int = 0
    regular_hits: int = 0
    last_updated: str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class GameConfig(BaseModel):
    colors: dict[str, int]
    character_favorites: dict[str, list[str]]
    bonus_probability: float


class GameState(BaseModel):
    is_active: bool = False
    started_at: datetime | None
    ended_at: datetime | None
    current_players: list[str] = []


# Game configuration
GAME_CONFIG = GameConfig(
    colors={
        "red": 100,
        "blue": 75,
        "green": 60,
        "yellow": 50,
        "purple": 40,
        "brown": 35,
        "orange": 45,
        "pink": 55,
        "gold": 90,
        "grey": 70,
        "white": 80,
        "black": 85,
    },
    character_favorites={
        "Jerry": ["brown", "yellow"],
        "Tom": ["grey", "blue"],
        "Mickey": ["red", "black"],
        "Donald": ["blue", "white"],
        "Bugs_Bunny": ["grey", "orange"],
        "Daffy_Duck": ["black", "orange"],
        "SpongeBob": ["yellow", "brown"],
        "Patrick": ["pink", "green"],
        "Pikachu": ["yellow", "red"],
        "Mario": ["red", "blue"],
        "Sonic": ["blue", "gold"],
        "Woody": ["brown", "yellow"],
        "Buzz": ["green", "purple"],
        "Scooby": ["brown", "green"],
        "Popeye": ["blue", "red"],
        "Pink_Panther": ["pink", "purple"],
        "Road_Runner": ["blue", "purple"],
        "Tweety": ["yellow", "orange"],
    },
    bonus_probability=float(os.getenv("BONUS_PROBABILITY", "0.15")),
)
