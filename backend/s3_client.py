"""
DEPRECATED: Legacy S3 client module for backward compatibility.

This module is deprecated. Use modules.file_storage instead:
    from modules.file_storage import s3_client, file_manager

This file exists only to maintain backward compatibility during the migration.
"""

import warnings
from modules.file_storage import *

warnings.warn(
    "s3_client.py is deprecated. Use 'from modules.file_storage import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)