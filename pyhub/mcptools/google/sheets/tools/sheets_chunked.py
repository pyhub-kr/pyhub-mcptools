"""Chunked data operations for Google Sheets.

These tools handle large datasets efficiently by processing data in chunks.
"""

import logging

from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.validators import validate_range_format, validate_spreadsheet_id
from pyhub.mcptools.google.sheets.client_async import get_async_client as get_client
from pyhub.mcptools.google.sheets.utils import json_dumps, parse_sheet_range, resolve_field_value

logger = logging.getLogger(__name__)


def _get_enabled_gsheet_tools():
    """Check if Google Sheets tools are enabled"""
    return getattr(settings, "USE_GOOGLE_SHEETS", False)


@mcp.tool(
    description="""Read data from Google Sheets in chunks for large datasets.

Efficiently reads large amounts of data by processing in chunks.
Useful for datasets that exceed memory limits or API quotas.

Args:
- spreadsheet_id: Spreadsheet ID
- sheet_range: Range to read (e.g., "Sheet1!A1:Z1000")
- chunk_size: Number of rows per chunk (default: 1000, max: 5000)

Returns a series of chunks, each containing:
- values: Cell values for this chunk (2D array)
- chunk_number: Current chunk number (1-based)
- row_offset: Starting row number for this chunk
- has_more: Whether more chunks are available
- total_rows_read: Total rows read so far""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
@validate_spreadsheet_id
@validate_range_format
async def gsheet_read_chunked(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    sheet_range: str = Field(description="Range to read (e.g., 'Sheet1!A1:Z1000')"),
    chunk_size: int = Field(default=1000, description="Number of rows per chunk", gt=0, le=5000),
) -> str:
    """Read large dataset in chunks"""
    # Ensure chunk_size is an integer, not a Field object
    chunk_size = resolve_field_value(chunk_size)

    client = get_client()
    sheet_name, range_str = parse_sheet_range(sheet_range)

    # Get spreadsheet info to determine total rows
    info = await client.get_spreadsheet_info(spreadsheet_id)
    sheet_info = next((s for s in info["sheets"] if s["name"] == sheet_name), None)

    if not sheet_info:
        return json_dumps({"error": f"Sheet '{sheet_name}' not found in spreadsheet"})

    total_rows = sheet_info["rowCount"]
    chunks_data = []
    current_row = 1
    chunk_number = 0

    # Parse range to get column bounds
    if range_str and ":" in range_str:
        start_cell, end_cell = range_str.split(":")
        # Extract column letters
        import re

        start_col = re.match(r"([A-Z]+)", start_cell).group(1)
        end_col = re.match(r"([A-Z]+)", end_cell).group(1)

        # Extract row numbers if specified
        start_row_match = re.match(r"[A-Z]+(\d+)", start_cell)
        end_row_match = re.match(r"[A-Z]+(\d+)", end_cell)

        if start_row_match:
            current_row = int(start_row_match.group(1))
        if end_row_match:
            total_rows = min(total_rows, int(end_row_match.group(1)))
    else:
        # Single cell or no range specified
        start_col = "A"
        end_col = "Z"  # Default to reasonable column range

    # Read data in chunks
    while current_row <= total_rows:
        chunk_number += 1
        end_row = min(current_row + chunk_size - 1, total_rows)

        # Construct range for this chunk
        chunk_range = f"{sheet_name}!{start_col}{current_row}:{end_col}{end_row}"

        try:
            values = await client.get_values(spreadsheet_id, sheet_name, f"{start_col}{current_row}:{end_col}{end_row}")

            chunk_data = {
                "values": values,
                "chunk_number": chunk_number,
                "row_offset": current_row,
                "rows_in_chunk": len(values),
                "has_more": end_row < total_rows,
                "total_rows_read": end_row,
                "chunk_range": chunk_range,
            }

            chunks_data.append(chunk_data)

            # Log progress
            logger.info(f"Read chunk {chunk_number}: rows {current_row}-{end_row} " f"({len(values)} rows)")

        except Exception as e:
            logger.error(f"Error reading chunk {chunk_number}: {e}")
            chunk_data = {
                "error": str(e),
                "chunk_number": chunk_number,
                "row_offset": current_row,
                "chunk_range": chunk_range,
            }
            chunks_data.append(chunk_data)
            break

        current_row = end_row + 1

        # Limit total chunks to prevent runaway reads
        if chunk_number >= 100:
            logger.warning("Reached maximum chunk limit (100)")
            break

    return json_dumps(
        {
            "chunks": chunks_data,
            "total_chunks": len(chunks_data),
            "total_rows_read": chunks_data[-1]["total_rows_read"] if chunks_data else 0,
            "chunk_size": chunk_size,
        }
    )


@mcp.tool(
    description="""Write data to Google Sheets in chunks for large datasets.

Efficiently writes large amounts of data by processing in chunks.
Prevents timeouts and memory issues when writing large datasets.

Args:
- spreadsheet_id: Spreadsheet ID
- sheet_range: Starting range for write (e.g., "Sheet1!A1")
- values: Complete dataset as 2D array
- chunk_size: Number of rows per chunk (default: 1000, max: 5000)
- batch_mode: Whether to use batch update API (faster but uses more quota)

Returns:
- total_cells_updated: Total number of cells written
- chunks_written: Number of chunks processed
- time_elapsed: Total time taken in seconds""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
@validate_spreadsheet_id
@validate_range_format
async def gsheet_write_chunked(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    sheet_range: str = Field(description="Starting range (e.g., 'Sheet1!A1')"),
    values: list[list[any]] = Field(description="Data to write as 2D array"),
    chunk_size: int = Field(default=1000, description="Number of rows per chunk", gt=0, le=5000),
    batch_mode: bool = Field(default=True, description="Use batch update API (faster)"),
) -> str:
    """Write large dataset in chunks"""
    # Ensure parameters are proper types, not Field objects
    chunk_size = resolve_field_value(chunk_size)
    batch_mode = resolve_field_value(batch_mode)

    import time

    start_time = time.time()

    client = get_client()
    sheet_name, start_cell = parse_sheet_range(sheet_range)

    if not values:
        return json_dumps({"error": "No data provided to write"})

    # Extract starting position
    import re

    cell_match = re.match(r"([A-Z]+)(\d+)", start_cell or "A1")
    if not cell_match:
        return json_dumps({"error": f"Invalid starting cell: {start_cell}"})

    start_col = cell_match.group(1)
    start_row = int(cell_match.group(2))

    total_rows = len(values)
    chunks_written = 0
    cells_updated = 0

    # Process data in chunks
    for chunk_start in range(0, total_rows, chunk_size):
        chunk_end = min(chunk_start + chunk_size, total_rows)
        chunk_data = values[chunk_start:chunk_end]

        # Calculate range for this chunk
        current_row = start_row + chunk_start
        end_row = current_row + len(chunk_data) - 1

        # Find maximum columns in chunk
        max_cols = max(len(row) for row in chunk_data) if chunk_data else 0
        if max_cols == 0:
            continue

        # Convert column number to letter (simplified for common cases)
        end_col_num = ord(start_col) - ord("A") + max_cols
        if end_col_num <= 26:
            end_col = chr(ord("A") + end_col_num - 1)
        else:
            # Handle multi-letter columns
            end_col = ""
            while end_col_num > 0:
                end_col_num -= 1
                end_col = chr(ord("A") + end_col_num % 26) + end_col
                end_col_num //= 26

        chunk_range = f"{sheet_name}!{start_col}{current_row}:{end_col}{end_row}"

        try:
            if batch_mode:
                # Use batch update for better performance
                result = await client.batch_update_values(spreadsheet_id, [(chunk_range, chunk_data)])
                cells_in_chunk = sum(len(row) for row in chunk_data)
            else:
                # Use regular update
                result = await client.update_values(spreadsheet_id, sheet_name, f"{start_col}{current_row}", chunk_data)
                cells_in_chunk = result["updatedCells"]

            chunks_written += 1
            cells_updated += cells_in_chunk

            logger.info(
                f"Wrote chunk {chunks_written}: rows {chunk_start + 1}-{chunk_end} " f"({cells_in_chunk} cells)"
            )

        except Exception as e:
            logger.error(f"Error writing chunk {chunks_written + 1}: {e}")
            return json_dumps(
                {
                    "error": str(e),
                    "chunks_written": chunks_written,
                    "cells_updated": cells_updated,
                    "failed_at_row": chunk_start + 1,
                }
            )

    elapsed_time = time.time() - start_time

    return json_dumps(
        {
            "total_cells_updated": cells_updated,
            "chunks_written": chunks_written,
            "total_rows": total_rows,
            "chunk_size": chunk_size,
            "time_elapsed": round(elapsed_time, 2),
            "cells_per_second": round(cells_updated / elapsed_time, 2) if elapsed_time > 0 else 0,
            "batch_mode": batch_mode,
        }
    )
