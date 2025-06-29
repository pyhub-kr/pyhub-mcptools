"""Batch operations for Google Sheets.

These tools allow multiple operations to be performed in a single API call
for better performance and quota efficiency.
"""

import logging
from typing import Any

from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.validators import validate_spreadsheet_id
from pyhub.mcptools.google.sheets.client_async import get_async_client as get_client
from pyhub.mcptools.google.sheets.utils import json_dumps

logger = logging.getLogger(__name__)


def _get_enabled_gsheet_tools():
    """Check if Google Sheets tools are enabled"""
    return getattr(settings, "USE_GOOGLE_SHEETS", False)


@mcp.tool(
    description="""Perform multiple read operations in a single batch request.

Efficiently reads multiple ranges from the same spreadsheet in one API call.
Significantly faster than multiple individual read operations.

Args:
- spreadsheet_id: Spreadsheet ID
- ranges: List of ranges to read (e.g., ["Sheet1!A1:B10", "Sheet2!C1:D5"])

Returns:
- results: List of read results for each range
  - range: The range that was read
  - values: Cell values (2D array)
  - rowCount: Number of rows
  - columnCount: Number of columns
- total_ranges: Number of ranges processed
- total_cells: Total number of cells read""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
@validate_spreadsheet_id
async def gsheet_batch_read(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    ranges: list[str] = Field(description="List of ranges to read"),
) -> str:
    """Read multiple ranges in a single batch operation"""
    if not ranges:
        return json_dumps({"error": "No ranges provided"})

    if len(ranges) > 100:
        return json_dumps({"error": "Maximum 100 ranges allowed per batch"})

    client = get_client()

    try:
        # Use batch get values API
        batch_results = await client.batch_get_values(spreadsheet_id, ranges)

        results = []
        total_cells = 0

        for i, range_name in enumerate(ranges):
            if i < len(batch_results):
                values = batch_results[i]
                row_count = len(values)
                col_count = len(values[0]) if values else 0
                cell_count = sum(len(row) for row in values)
                total_cells += cell_count

                results.append(
                    {
                        "range": range_name,
                        "values": values,
                        "rowCount": row_count,
                        "columnCount": col_count,
                        "cellCount": cell_count,
                    }
                )
            else:
                results.append(
                    {
                        "range": range_name,
                        "error": "No data returned for this range",
                        "values": [],
                        "rowCount": 0,
                        "columnCount": 0,
                        "cellCount": 0,
                    }
                )

        return json_dumps(
            {
                "results": results,
                "total_ranges": len(ranges),
                "total_cells": total_cells,
                "successful_ranges": len([r for r in results if "error" not in r]),
            }
        )

    except Exception as e:
        logger.error(f"Batch read error: {e}")
        return json_dumps({"error": str(e), "ranges_requested": ranges})


@mcp.tool(
    description="""Perform multiple write operations in a single batch request.

Efficiently writes to multiple ranges in the same spreadsheet in one API call.
Much faster than individual write operations and uses less API quota.

Args:
- spreadsheet_id: Spreadsheet ID
- updates: List of range updates
  Each update should have:
  - range: Target range (e.g., "Sheet1!A1:B5")
  - values: Data to write (2D array)

Returns:
- total_cells_updated: Total number of cells updated
- ranges_updated: Number of ranges processed
- updates_summary: Details for each range update""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
@validate_spreadsheet_id
async def gsheet_batch_write(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    updates: list[dict[str, Any]] = Field(description="List of range updates with 'range' and 'values' keys"),
) -> str:
    """Write to multiple ranges in a single batch operation"""
    if not updates:
        return json_dumps({"error": "No updates provided"})

    if len(updates) > 100:
        return json_dumps({"error": "Maximum 100 updates allowed per batch"})

    # Validate update format
    for i, update in enumerate(updates):
        if not isinstance(update, dict):
            return json_dumps({"error": f"Update {i} must be a dictionary"})
        if "range" not in update or "values" not in update:
            return json_dumps({"error": f"Update {i} must have 'range' and 'values' keys"})

    client = get_client()

    try:
        # Prepare batch update data
        range_updates = []
        for update in updates:
            range_updates.append((update["range"], update["values"]))

        # Perform batch update
        result = await client.batch_update_values(spreadsheet_id, range_updates)

        # Process results
        updates_summary = []
        total_cells = 0

        for _i, update in enumerate(updates):
            values = update["values"]
            if isinstance(values, list):
                cell_count = sum(len(row) if isinstance(row, list) else 1 for row in values)
            else:
                cell_count = 1

            total_cells += cell_count

            updates_summary.append(
                {
                    "range": update["range"],
                    "cells_updated": cell_count,
                    "rows_updated": len(values) if isinstance(values, list) else 1,
                    "status": "success",
                }
            )

        return json_dumps(
            {
                "total_cells_updated": total_cells,
                "ranges_updated": len(updates),
                "updates_summary": updates_summary,
                "batch_update_id": result.get("spreadsheetId", spreadsheet_id),
            }
        )

    except Exception as e:
        logger.error(f"Batch write error: {e}")
        return json_dumps({"error": str(e), "updates_attempted": len(updates)})


@mcp.tool(
    description="""Clear multiple ranges in a single batch operation.

Efficiently clears content from multiple ranges in one API call.

Args:
- spreadsheet_id: Spreadsheet ID
- ranges: List of ranges to clear (e.g., ["Sheet1!A1:B10", "Sheet2!C1:D5"])

Returns:
- ranges_cleared: Number of ranges cleared
- cleared_ranges: List of successfully cleared ranges""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
@validate_spreadsheet_id
async def gsheet_batch_clear(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    ranges: list[str] = Field(description="List of ranges to clear"),
) -> str:
    """Clear multiple ranges in a single batch operation"""
    if not ranges:
        return json_dumps({"error": "No ranges provided"})

    if len(ranges) > 100:
        return json_dumps({"error": "Maximum 100 ranges allowed per batch"})

    client = get_client()

    try:
        # Perform batch clear
        await client.batch_clear_values(spreadsheet_id, ranges)

        return json_dumps({"ranges_cleared": len(ranges), "cleared_ranges": ranges, "spreadsheet_id": spreadsheet_id})

    except Exception as e:
        logger.error(f"Batch clear error: {e}")
        return json_dumps({"error": str(e), "ranges_requested": ranges})


@mcp.tool(
    description="""Copy data between multiple ranges in batch.

Efficiently copies data from source ranges to destination ranges.
All operations are performed in a single batch for optimal performance.

Args:
- spreadsheet_id: Spreadsheet ID (can be same for source and destination)
- copy_operations: List of copy operations
  Each operation should have:
  - source_range: Source range (e.g., "Sheet1!A1:B5")
  - dest_range: Destination range (e.g., "Sheet2!C1")
  - source_spreadsheet_id: Optional source spreadsheet ID (defaults to main spreadsheet_id)

Returns:
- operations_completed: Number of copy operations performed
- total_cells_copied: Total number of cells copied
- operations_summary: Details for each copy operation""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
@validate_spreadsheet_id
async def gsheet_batch_copy(
    spreadsheet_id: str = Field(description="Primary spreadsheet ID"),
    copy_operations: list[dict[str, Any]] = Field(
        description="List of copy operations with source_range and dest_range"
    ),
) -> str:
    """Copy data between multiple ranges in batch"""
    if not copy_operations:
        return json_dumps({"error": "No copy operations provided"})

    if len(copy_operations) > 50:
        return json_dumps({"error": "Maximum 50 copy operations allowed per batch"})

    # Validate operation format
    for i, op in enumerate(copy_operations):
        if not isinstance(op, dict):
            return json_dumps({"error": f"Operation {i} must be a dictionary"})
        if "source_range" not in op or "dest_range" not in op:
            return json_dumps({"error": f"Operation {i} must have 'source_range' and 'dest_range' keys"})

    client = get_client()

    try:
        # First, read all source ranges
        source_ranges = []
        source_spreadsheets = {}

        for op in copy_operations:
            source_id = op.get("source_spreadsheet_id", spreadsheet_id)
            source_range = op["source_range"]

            if source_id not in source_spreadsheets:
                source_spreadsheets[source_id] = []
            source_spreadsheets[source_id].append(source_range)
            source_ranges.append((source_id, source_range))

        # Read all source data
        read_results = {}
        for src_id, ranges in source_spreadsheets.items():
            batch_data = await client.batch_get_values(src_id, ranges)
            for i, range_name in enumerate(ranges):
                read_results[(src_id, range_name)] = batch_data[i] if i < len(batch_data) else []

        # Prepare write operations
        write_operations = []
        operations_summary = []
        total_cells = 0

        for _i, op in enumerate(copy_operations):
            source_id = op.get("source_spreadsheet_id", spreadsheet_id)
            source_range = op["source_range"]
            dest_range = op["dest_range"]

            # Get source data
            source_data = read_results.get((source_id, source_range), [])

            if source_data:
                write_operations.append((dest_range, source_data))
                cell_count = sum(len(row) if isinstance(row, list) else 1 for row in source_data)
                total_cells += cell_count

                operations_summary.append(
                    {
                        "source_range": source_range,
                        "dest_range": dest_range,
                        "source_spreadsheet_id": source_id,
                        "cells_copied": cell_count,
                        "rows_copied": len(source_data),
                        "status": "success",
                    }
                )
            else:
                operations_summary.append(
                    {
                        "source_range": source_range,
                        "dest_range": dest_range,
                        "source_spreadsheet_id": source_id,
                        "cells_copied": 0,
                        "rows_copied": 0,
                        "status": "no_data",
                    }
                )

        # Perform batch write to destination
        if write_operations:
            await client.batch_update_values(spreadsheet_id, write_operations)

        return json_dumps(
            {
                "operations_completed": len(copy_operations),
                "total_cells_copied": total_cells,
                "operations_summary": operations_summary,
                "destination_spreadsheet_id": spreadsheet_id,
            }
        )

    except Exception as e:
        logger.error(f"Batch copy error: {e}")
        return json_dumps({"error": str(e), "operations_attempted": len(copy_operations)})
