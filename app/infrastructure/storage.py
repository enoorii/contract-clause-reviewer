from pathlib import Path

import anyio

from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


async def delete_file_async(file_path: str | Path) -> bool:
    """
    Asynchronously delete a file using anyio.

    Args:
        file_path: Path to the file to delete

    Returns:
        bool: True if file was deleted or doesn't exist, False if deletion failed
    """

    # Check if file exists
    if not await anyio.Path(file_path).exists():
        return True

    try:
        await anyio.Path(file_path).unlink()
        logger.info(f"Successfully deleted file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {e}")
        return False
