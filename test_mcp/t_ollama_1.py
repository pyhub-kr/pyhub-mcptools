import ollama
from mcp import StdioServerParameters, stdio_client, ClientSession

# OLLAMA_MODEL = "llama3.1:8b"  # 필요시 ollama list로 설치 모델 확인

OLLAMA_MODEL = "qwen3:8b"


server_params = StdioServerParameters(
    command="/Users/allieus/mcptools/pyhub.mcptools/pyhub.mcptools",
    args=["run", "stdio"],
    env=None,
)


def excel_get_opened_workbooks():
    """
    Get a list of all open workbooks and their sheets in Excel                                                          │
                                                                                                                        │
    Returns:                                                                                                            │
        str: JSON string containing:                                                                                    │
            - books: List of open workbooks                                                                             │
                - name: Workbook name                                                                                   │
                - fullname: Full path of workbook                                                                       │
                - sheets: List of sheets in workbook                                                                    │
                    - name: Sheet name                                                                                  │
                    - index: Sheet index                                                                                │
                    - range: Used range address (e.g. "$A$1:$E$665")                                                    │
                    - count: Total number of cells in used range                                                        │
                    - shape: Tuple of (rows, columns) in used range                                                     │
                    - active: Whether this is the active sheet                                                          │
                - active: Whether this is the active workbook
    """

    return {
        "books": [
            {
                "name": "통합 문서1",
                "fullname": "통합 문서1",
                "sheets": [
                    {
                        "name": "Sheet1",
                        "index": 1,
                        "range": "$A$1",
                        "count": 1,
                        "shape": [1, 1],
                        "active": True,
                        "table_names": [],
                    }
                ],
                "active": True,
            }
        ]
    }


def excel_set_values(sheet_range: str, values: str) -> str:
    """
    Write data to a specified range in an Excel workbook.

    Performance Tips:
        - When setting values to multiple consecutive cells, it's more efficient to use a single
    call
          with a range (e.g. "A1:B10") rather than making multiple calls for individual cells.
        - For large datasets, using CSV format with range notation is significantly faster than
          making separate calls for each cell.

    Args:
        sheet_range: Excel range where to write the data.
        values: CSV string. Values containing commas must be enclosed in double quotes

    Returns:
        str: Success message indicating values were set.

    Examples:
        >>> func(sheet_range="A1", values="v1,v2,v3\nv4,v5,v6")  # grid using CSV
        >>> func(sheet_range="A1:B3", values="1,2\n3,4\n5,6")  # faster than 6 separate calls
        >>> func(sheet_range="Sheet1!A1:C2", values="[[1,2,3],[4,5,6]]")  # using JSON array
        >>> func(csv_abs_path="/path/to/data.csv", sheet_range="A1")  # import from CSV file
    """
    return "ok"


async def main():

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            user_message = input(">>>")

            response = ollama.chat(
                "llama3.1:8b",
                messages=[{"role": "user", "content": user_message}],
                tools=[excel_get_opened_workbooks, excel_set_values],  # Actual function reference
            )

            for tool in response.message.tool_calls or []:
                if tool.function.name == "excel_get_opened_workbooks":
                    function_response = excel_get_opened_workbooks(**tool.function.arguments)
                    print("function_response :", repr(function_response))
                elif tool.function.name == "excel_set_values":
                    print("호출이 들어갑니다 !!!")
                    tool_response = await session.call_tool("excel_set_values", arguments=tool.function.arguments)
                    print("tool_response :", repr(tool_response))
                else:
                    print("not found tool :", tool.function.name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
