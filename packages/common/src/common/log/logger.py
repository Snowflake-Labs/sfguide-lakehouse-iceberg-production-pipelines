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

import logging
import os
import time


class LocalTimezoneFormatter(logging.Formatter):
    """Custom formatter that uses local timezone"""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None) -> str:
        # Convert UTC to local time
        ct = self.converter(record.created)
        if datefmt:
            return time.strftime(datefmt, ct)
        return time.strftime("%Y-%m-%d %H:%M:%S", ct)


# Define format
FORMATTER = LocalTimezoneFormatter(
    fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(
    name: str = __name__,
    level: int = os.getenv("APP_LOG_LEVEL", logging.WARNING),
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    #
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Console handler
    add_handler_to_logger(logger)

    return logger


def add_handler_to_logger(logger):
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(FORMATTER)
    logger.addHandler(console_handler)
