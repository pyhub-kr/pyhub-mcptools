import asyncio
import ollama
import typer
from mcp import ClientSession, StdioServerParameters, types, ListToolsResult
from mcp.client.stdio import stdio_client
from rich.console import Console
from rich.prompt import Prompt

OLLAMA_MODEL = "qwen3:8b"  # 필요시 ollama list로 설치 모델 확인

console = Console()

server_params = StdioServerParameters(
    command="/Users/allieus/mcptools/pyhub.mcptools/pyhub.mcptools",
    args=["run", "stdio"],
    env=None,
)


async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def tool_call(_func_name: str, _func_arguments) -> dict:
                print("tool_call :", _func_name, _func_arguments)

                if _func_name == "get_temperature":
                    return {
                        "role": "function",
                        "name": _func_name,
                        "content": "12.3",
                    }

                else:
                    tool_response = await session.call_tool(_func_name, arguments=_func_arguments)
                    print("tool_response :", repr(tool_response))
                    return {
                        "role": "function",
                        "name": _func_name,
                        "content": str(tool_response),
                    }

            function_calling_tools = []

            with console.status("[bold green]Loading available tools..."):
                list_tools_result: ListToolsResult = await session.list_tools()
                for tool in list_tools_result.tools:
                    if tool.name in ("excel_set_values",):
                        print("tool :", tool.name)
                        function_calling_tools.append(
                            {
                                "type": "function",
                                "function": {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "parameters": tool.inputSchema,
                                },
                            }
                        )

                    if len(function_calling_tools) > 5:
                        break

            messages = []

            while True:
                try:
                    user_input = Prompt.ask("\n[bold green]You[/]").strip()
                except (KeyboardInterrupt, EOFError):
                    break

                if not user_input:
                    break

                messages.append({"role": "user", "content": user_input})

                console.print("\n[bold blue]Assistant[/]: ", end="")

                with console.status("[bold yellow]Thinking...", spinner="dots") as status:
                    while True:
                        buffer = ""
                        run_tool = False

                        for response in ollama.chat(
                            model=OLLAMA_MODEL,
                            messages=messages,
                            stream=True,
                            tools=function_calling_tools,
                        ):
                            if response.message.content:
                                message_content = response.message.content
                                buffer += message_content
                                status.update(buffer)

                            elif response.message.tool_calls:
                                console.print(
                                    f"[yellow]Found {len(response.message.tool_calls)} tool call(s) to process..."
                                )

                                for tool in response.message.tool_calls:
                                    ai_message = await tool_call(
                                        tool.function.name,
                                        tool.function.arguments,
                                    )
                                    messages.append(ai_message)

                                run_tool = True

                        if buffer:
                            messages.append(
                                {
                                    "role": "assistant",
                                    "content": buffer,
                                }
                            )
                            console.print(f"AI: {buffer}")

                        if run_tool:
                            continue
                        else:
                            break

                    status.stop()


def main():
    """Python MCP Tools - Interactive Chat Interface"""
    try:
        console.print("[bold cyan]Welcome to Python MCP Tools![/]")
        console.print("[dim]Press Ctrl+C to exit[/]\n")
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[bold red]Goodbye![/]")
    except Exception as e:
        import traceback

        traceback.print_exc()
        console.print(f"\n[bold red]Unhandled Error:[/] {str(e)}")
        raise typer.Exit(1)


if __name__ == "__main__":
    typer.run(main)
