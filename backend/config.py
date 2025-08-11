"""
DEPRECATED: Legacy config module for backward compatibility.

This module is deprecated. Use modules.config instead:
    from modules.config import config_manager, get_app_settings, etc.

This file exists only to maintain backward compatibility during the migration.
"""

import warnings
from modules.config import *

warnings.warn(
    "config.py is deprecated. Use 'from modules.config import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)