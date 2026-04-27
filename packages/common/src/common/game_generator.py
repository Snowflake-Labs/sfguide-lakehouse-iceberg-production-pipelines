#!/usr/bin/env python3

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
"""Deterministic BalloonGameGenerator for bronze Iceberg data loading.

Provides a seed-based, reproducible event generator used by
``tools/bronze_preload/load_sample.py`` to synthesise ``balloon_game_events``
rows. Unlike the streaming Kafka producer, this class accepts an explicit
``rng`` for reproducibility and an ``event_ts`` per pop for synthetic
timelines.

Key env vars (read indirectly via GAME_CONFIG):
  BONUS_PROBABILITY  override default bonus hit probability
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from common.stream.models import GAME_CONFIG, GameEvent


class BalloonGameGenerator:
    """Generate reproducible balloon-pop events for bronze data loading.

    Parameters
    ----------
    bonus_probability:
        Probability that a given pop is a favourite-colour bonus hit.
    rng:
        Optional seeded :class:`random.Random` instance. When provided,
        all random choices draw from this instance so event sequences are
        fully deterministic for a given seed.
    """

    def __init__(
        self,
        bonus_probability: float,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self.bonus_probability = bonus_probability
        self._rng = rng or random.Random()
        self._colors = list(GAME_CONFIG.colors.keys())
        self._char_favorites = GAME_CONFIG.character_favorites
        self._characters = list(GAME_CONFIG.character_favorites.keys())

    def generate_pop(
        self,
        player: str,
        *,
        event_ts: datetime | None = None,
    ) -> GameEvent:
        """Generate a single balloon-pop event.

        Parameters
        ----------
        player:
            Player name for this event.
        event_ts:
            Timestamp for the event. Defaults to ``datetime.now(timezone.utc)``.
        """
        rng = self._rng
        # Pick a reference character to determine favourite-colour eligibility.
        character = rng.choice(self._characters)
        favorites = self._char_favorites.get(character, [])

        if favorites and rng.random() < self.bonus_probability:
            balloon_color = rng.choice(favorites)
            favorite_color_bonus = True
        else:
            balloon_color = rng.choice(self._colors)
            favorite_color_bonus = balloon_color in favorites

        score = GAME_CONFIG.colors.get(balloon_color, 0)
        ts = event_ts or datetime.now(timezone.utc)
        return GameEvent(
            player=player,
            balloon_color=balloon_color,
            score=score,
            favorite_color_bonus=favorite_color_bonus,
            event_ts=ts.isoformat().replace("+00:00", "Z"),
        )
