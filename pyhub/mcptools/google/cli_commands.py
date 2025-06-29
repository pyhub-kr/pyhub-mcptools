"""Google-specific CLI commands."""

import asyncio
import os

import typer
from rich.console import Console

from pyhub.mcptools.core.cli import app
from pyhub.mcptools.google.gmail.auth import GmailAuth
from pyhub.mcptools.google.gmail.client_async import get_gmail_client
from pyhub.mcptools.google.sheets.auth import GoogleSheetsAuth
from pyhub.mcptools.google.sheets.client_async import get_async_client

console = Console()

# Create Google subcommand group
google_app = typer.Typer(name="google")
app.add_typer(google_app, name="google")


@google_app.command("auth")
def auth_command(
    status: bool = typer.Option(False, "--status", help="인증 상태 확인"),
    refresh: bool = typer.Option(False, "--refresh", help="토큰 갱신"),
    clear: bool = typer.Option(False, "--clear", help="저장된 토큰 삭제"),
    force: bool = typer.Option(False, "--force", help="강제 재인증"),
):
    """Google API 인증 관리"""
    # Ensure Google Sheets is enabled
    os.environ.setdefault("USE_GOOGLE_SHEETS", "1")

    auth = GoogleSheetsAuth()

    if status:
        # 인증 상태 확인
        console.print("🔍 인증 상태 확인 중...")

        if not auth.token_file.exists():
            console.print("❌ 저장된 인증 토큰이 없습니다.")
            console.print(f"   토큰 위치: {auth.token_file}")
            raise typer.Exit(1)

        try:
            creds = auth.get_credentials()
            if creds and creds.valid:
                console.print("✅ 유효한 인증 토큰이 있습니다.")
                console.print(f"   토큰 위치: {auth.token_file}")
                if hasattr(creds, "expiry") and creds.expiry:
                    console.print(f"   만료 시간: {creds.expiry}")
            else:
                console.print("⚠️  토큰이 만료되었거나 유효하지 않습니다.")
                console.print("   'python -m pyhub.mcptools.google google auth --refresh'로 갱신하세요.")
        except Exception as e:
            console.print(f"❌ 토큰 확인 중 오류: {e}")
            raise typer.Exit(1) from e

    elif refresh:
        # 토큰 갱신
        console.print("🔄 토큰 갱신 중...")
        try:
            creds = auth.get_credentials()
            if creds:
                console.print("✅ 토큰이 갱신되었습니다.")
            else:
                console.print("❌ 토큰 갱신에 실패했습니다.")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"❌ 갱신 중 오류: {e}")
            raise typer.Exit(1) from e

    elif clear:
        # 토큰 삭제
        if auth.token_file.exists():
            auth.token_file.unlink()
            console.print("✅ 인증 토큰이 삭제되었습니다.")
            console.print(f"   삭제된 파일: {auth.token_file}")
        else:
            console.print("ℹ️  삭제할 토큰이 없습니다.")

    else:
        # 새로운 인증
        console.print("🔐 Google Sheets API 인증을 시작합니다...")

        # 클라이언트 시크릿 확인
        if not auth.client_secret_path.exists():
            console.print(f"❌ 클라이언트 시크릿 파일이 없습니다: {auth.client_secret_path}")
            console.print("\n다음 단계를 따라주세요:")
            console.print("1. Google Cloud Console (https://console.cloud.google.com) 접속")
            console.print("2. 프로젝트 생성 또는 선택")
            console.print("3. Google Sheets API 활성화")
            console.print("4. OAuth 2.0 클라이언트 ID 생성")
            console.print("5. JSON 파일 다운로드")
            console.print(f"6. 파일을 다음 위치에 저장: {auth.client_secret_path}")
            raise typer.Exit(1)

        # 기존 토큰 삭제 여부 확인
        if auth.token_file.exists() and not force:
            console.print("⚠️  기존 인증 토큰이 있습니다.")
            console.print("   --force 옵션을 사용하여 재인증하거나")
            console.print("   --refresh 옵션으로 토큰을 갱신하세요.")
            raise typer.Exit(1)

        try:
            # 기존 토큰 삭제
            if auth.token_file.exists():
                auth.token_file.unlink()

            # 새 인증 진행
            creds = auth.get_credentials()
            if creds and creds.valid:
                console.print("✅ 인증이 완료되었습니다!")
                console.print(f"   토큰 저장 위치: {auth.token_file}")
            else:
                console.print("❌ 인증에 실패했습니다.")
                raise typer.Exit(1)

        except Exception as e:
            console.print(f"❌ 인증 중 오류 발생: {e}")
            raise typer.Exit(1) from e


@google_app.command("test")
def test_command():
    """Google Sheets API 연결 테스트"""
    console.print("🧪 Google Sheets API 연결 테스트...")

    auth = GoogleSheetsAuth()

    # 인증 확인
    try:
        creds = auth.get_credentials()
        if not creds or not creds.valid:
            console.print("❌ 유효한 인증이 없습니다.")
            console.print("   먼저 'python -m pyhub.mcptools.google google auth'를 실행하세요.")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ 인증 확인 실패: {e}")
        raise typer.Exit(1) from e

    # API 연결 테스트
    console.print("📡 API 연결 테스트 중...")

    async def test_connection():
        try:
            client = get_async_client()
            # 간단한 API 호출 (스프레드시트 목록 조회)
            spreadsheets = await client.list_spreadsheets()
            return True, len(spreadsheets)
        except Exception as e:
            return False, str(e)

    success, result = asyncio.run(test_connection())

    if success:
        console.print(f"✅ API 연결 성공! (스프레드시트 {result}개 발견)")
    else:
        console.print(f"❌ API 연결 실패: {result}")
        raise typer.Exit(1)


# Sheets subcommands
sheets_app = typer.Typer(name="sheets")
google_app.add_typer(sheets_app, name="sheets")


@sheets_app.command("list")
def sheets_list(
    limit: int = typer.Option(10, "--limit", help="목록 제한 (기본: 10)"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """스프레드시트 목록 조회"""

    async def _list_sheets():
        try:
            client = get_async_client()
            spreadsheets = await client.list_spreadsheets()

            # 제한 적용
            spreadsheets = spreadsheets[:limit]

            if json_output:
                from pyhub.mcptools.google.sheets.utils import json_dumps

                console.print(json_dumps(spreadsheets))
            else:
                console.print(f"📊 스프레드시트 목록 조회 중... (최대 {limit}개)")
                console.print(f"\n총 {len(spreadsheets)}개의 스프레드시트:")
                console.print("-" * 80)

                for i, sheet in enumerate(spreadsheets, 1):
                    console.print(f"  {i}. {sheet['name']}")
                    console.print(f"     ID: {sheet['id']}")
                    console.print(f"     수정: {sheet['modifiedTime']}")
                    if i < len(spreadsheets):
                        console.print()

        except Exception as e:
            console.print(f"❌ 목록 조회 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_list_sheets())


@sheets_app.command("search")
def sheets_search(
    search_term: str = typer.Argument(..., help="검색어"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """스프레드시트 검색"""

    async def _search_sheets():
        try:
            client = get_async_client()
            console.print(f"🔍 '{search_term}' 검색 중...")

            matches = await client.search_spreadsheets(search_term)

            if not matches:
                console.print(f"ℹ️  '{search_term}'와 일치하는 스프레드시트가 없습니다.")
                return

            if json_output:
                from pyhub.mcptools.google.sheets.utils import json_dumps

                console.print(json_dumps(matches))
            else:
                console.print(f"\n'{search_term}'와 일치하는 스프레드시트 {len(matches)}개:")
                console.print("-" * 80)

                for i, sheet in enumerate(matches, 1):
                    console.print(f"{i:3d}. {sheet['name']}")
                    console.print(f"     ID: {sheet['id']}")
                    console.print(f"     수정: {sheet['modifiedTime']}")
                    if i < len(matches):
                        console.print()

        except Exception as e:
            console.print(f"❌ 검색 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_search_sheets())


@sheets_app.command("create")
def sheets_create(
    name: str = typer.Argument(..., help="스프레드시트 이름"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """새 스프레드시트 생성"""

    async def _create_sheet():
        try:
            client = get_async_client()
            console.print(f"📄 새 스프레드시트 '{name}' 생성 중...")

            result = await client.create_spreadsheet(name)

            if json_output:
                from pyhub.mcptools.google.sheets.utils import json_dumps

                console.print(json_dumps(result))
            else:
                console.print("✅ 스프레드시트가 생성되었습니다!")
                console.print(f"   이름: {result['name']}")
                console.print(f"   ID: {result['id']}")
                console.print(f"   URL: {result['url']}")

        except Exception as e:
            console.print(f"❌ 생성 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_create_sheet())


@sheets_app.command("info")
def sheets_info(
    spreadsheet_id: str = typer.Argument(..., help="스프레드시트 ID"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """스프레드시트 정보 조회"""

    async def _get_info():
        try:
            client = get_async_client()
            console.print("📊 스프레드시트 정보 조회 중...")

            info = await client.get_spreadsheet_info(spreadsheet_id)

            if json_output:
                from pyhub.mcptools.google.sheets.utils import json_dumps

                console.print(json_dumps(info))
            else:
                console.print(f"📄 {info['name']}")
                console.print(f"   ID: {info['id']}")
                console.print(f"   URL: {info['url']}")
                console.print(f"   시트 수: {len(info['sheets'])}")
                console.print("\n📊 시트 목록:")
                for sheet in info["sheets"]:
                    console.print(f"  - {sheet['name']} ({sheet['rowCount']}x{sheet['columnCount']})")

        except Exception as e:
            console.print(f"❌ 정보 조회 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_get_info())


@sheets_app.command("read")
def sheets_read(
    spreadsheet_id: str = typer.Argument(..., help="스프레드시트 ID"),
    range_spec: str = typer.Argument(..., help="범위 (예: Sheet1!A1:C10)"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """데이터 읽기"""

    async def _read_data():
        try:
            client = get_async_client()
            from pyhub.mcptools.google.sheets.utils import parse_sheet_range

            sheet_name, range_str = parse_sheet_range(range_spec)
            console.print(f"📆 데이터 읽기 중: {range_spec}")

            values = await client.get_values(spreadsheet_id, sheet_name, range_str)

            if json_output:
                from pyhub.mcptools.google.sheets.utils import json_dumps

                console.print(json_dumps(values))
            else:
                if not values:
                    console.print("ℹ️  비어있는 범위입니다.")
                else:
                    console.print(f"\n📄 데이터 ({len(values)}행 x {len(values[0]) if values else 0}열):")
                    for i, row in enumerate(values):
                        row_str = "\t".join(str(cell) for cell in row)
                        console.print(f"  {i+1:3d}: {row_str}")

        except Exception as e:
            console.print(f"❌ 데이터 읽기 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_read_data())


@sheets_app.command("write")
def sheets_write(
    spreadsheet_id: str = typer.Argument(..., help="스프레드시트 ID"),
    range_spec: str = typer.Argument(..., help="범위 (예: Sheet1!A1)"),
    data: str = typer.Argument(..., help="데이터 (JSON 배열 형식)"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """데이터 쓰기"""

    async def _write_data():
        try:
            import json as std_json

            client = get_async_client()
            from pyhub.mcptools.google.sheets.utils import ensure_2d_array, parse_sheet_range

            # JSON 데이터 파싱
            try:
                parsed_data = std_json.loads(data)
                values = ensure_2d_array(parsed_data)
            except std_json.JSONDecodeError as e:
                console.print(f"❌ 잘못된 JSON 형식: {e}")
                raise typer.Exit(1) from e

            sheet_name, range_str = parse_sheet_range(range_spec)
            console.print(f"📝 데이터 쓰기 중: {range_spec}")

            result = await client.set_values(spreadsheet_id, sheet_name, range_str, values)

            if json_output:
                from pyhub.mcptools.google.sheets.utils import json_dumps

                console.print(json_dumps(result))
            else:
                console.print("✅ 데이터가 성공적으로 작성되었습니다!")
                console.print(f"   업데이트된 셀: {result.get('updatedCells', 0)}개")
                console.print(f"   업데이트된 범위: {result.get('updatedRange', range_spec)}")

        except Exception as e:
            console.print(f"❌ 데이터 쓰기 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_write_data())


# Gmail CLI Commands
gmail_app = typer.Typer(name="gmail", help="Gmail 이메일 관리")
google_app.add_typer(gmail_app, name="gmail")


@gmail_app.command("auth")
def gmail_auth_command(
    status: bool = typer.Option(False, "--status", help="Gmail 인증 상태 확인"),
    clear: bool = typer.Option(False, "--clear", help="저장된 Gmail 토큰 삭제"),
):
    """Gmail API 인증 관리"""
    auth = GmailAuth()

    if status:
        console.print("🔍 Gmail 인증 상태 확인 중...")

        if not auth.token_path.exists():
            console.print("❌ 저장된 Gmail 인증 토큰이 없습니다.")
            console.print(f"   토큰 위치: {auth.token_path}")
            raise typer.Exit(1)

        try:
            if auth.is_authenticated():
                console.print("✅ 유효한 Gmail 인증 토큰이 있습니다.")
                user_email = auth.get_user_email()
                if user_email:
                    console.print(f"   계정: {user_email}")
                console.print(f"   토큰 위치: {auth.token_path}")
            else:
                console.print("⚠️  Gmail 토큰이 만료되었거나 유효하지 않습니다.")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"❌ Gmail 인증 확인 실패: {e}")
            raise typer.Exit(1) from e
        return

    if clear:
        console.print("🗑️ Gmail 토큰 삭제 중...")
        try:
            auth.clear_credentials()
            console.print("✅ Gmail 토큰이 삭제되었습니다.")
        except Exception as e:
            console.print(f"❌ 토큰 삭제 실패: {e}")
            raise typer.Exit(1) from e
        return

    # 새로운 인증 시작
    console.print("🔐 Gmail API 인증을 시작합니다...")

    try:
        # 인증 수행
        auth.get_credentials()

        # 연결 테스트
        if auth.test_connection():
            user_email = auth.get_user_email()
            console.print("✅ Gmail 인증이 완료되었습니다!")
            if user_email:
                console.print(f"   계정: {user_email}")
            console.print(f"   토큰 저장 위치: {auth.token_path}")
        else:
            console.print("❌ Gmail 연결 테스트에 실패했습니다.")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"❌ Gmail 인증 실패: {e}")
        raise typer.Exit(1) from e


@gmail_app.command("test")
def gmail_test_command():
    """Gmail API 연결 테스트"""
    console.print("🧪 Gmail API 연결 테스트...")

    try:
        auth = GmailAuth()

        if auth.test_connection():
            user_email = auth.get_user_email()
            console.print("✅ Gmail API 연결 성공!")
            if user_email:
                console.print(f"   계정: {user_email}")
        else:
            console.print("❌ Gmail API 연결 실패")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"❌ Gmail 연결 테스트 실패: {e}")
        raise typer.Exit(1) from e


@gmail_app.command("list")
def gmail_list_command(
    query: str = typer.Option("", "--query", "-q", help="Gmail 검색 쿼리"),
    max_results: int = typer.Option(10, "--max", "-m", help="최대 조회 개수"),
    format: str = typer.Option("table", "--format", "-f", help="출력 형식 (minimal, detailed, table)"),
    include_metadata: bool = typer.Option(True, "--metadata/--no-metadata", help="메타데이터 포함 여부"),
    batch_size: int = typer.Option(5, "--batch-size", help="배치 조회 크기"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """Gmail 이메일 목록 조회 (개선된 버전)"""

    async def _list_emails():
        try:
            console.print("📧 Gmail 이메일 목록 조회 중...")

            client = await get_gmail_client()

            if include_metadata and format != "minimal":
                result = await client.list_messages_detailed(
                    query=query, max_results=max_results, batch_size=batch_size
                )
            else:
                result = await client.list_messages(query=query, max_results=max_results)

            if json_output:
                from pyhub.mcptools.google.sheets.utils import json_dumps

                console.print(json_dumps(result))
            else:
                _display_messages(result, format)

        except Exception as e:
            console.print(f"❌ 이메일 목록 조회 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_list_emails())


def _display_messages(result: dict, format: str):
    """메시지 목록 출력"""
    messages = result.get("messages", [])
    total_count = result.get("total_count", 0)
    query = result.get("query", "")

    console.print(f"✅ 이메일 {total_count}개를 찾았습니다.")

    if not messages:
        return

    if format == "minimal":
        _display_minimal(messages)
    elif format == "detailed":
        _display_detailed(messages)
    else:  # table
        _display_table(messages)

    if result.get("next_page_token"):
        console.print("\n💡 더 많은 결과가 있습니다.")

    if query:
        console.print(f"\n🔍 사용된 검색 쿼리: {query}")


def _display_minimal(messages: list):
    """간단한 형식으로 출력"""
    console.print("\n📋 이메일 목록 (간단):")
    for i, msg in enumerate(messages, 1):
        console.print(f"  {i}. ID: {msg.get('id', 'Unknown')}")
        console.print(f"     Thread ID: {msg.get('threadId', 'Unknown')}")


def _display_detailed(messages: list):
    """상세한 형식으로 출력"""
    console.print("\n📋 이메일 목록 (상세):")
    for i, msg in enumerate(messages, 1):
        status_icons = []
        if msg.get("is_unread"):
            status_icons.append("🔴")
        if msg.get("is_starred"):
            status_icons.append("⭐")
        if msg.get("is_important"):
            status_icons.append("❗")

        status_str = " ".join(status_icons) if status_icons else "✅"

        console.print(f"  {i}. {status_str} {msg.get('subject', '(제목 없음)')}")
        console.print(f"     발신자: {msg.get('from', 'Unknown')}")
        console.print(f"     날짜: {_format_date(msg.get('date', ''))}")
        console.print(f"     ID: {msg.get('id', 'Unknown')}")
        if i < len(messages):
            console.print()


def _display_table(messages: list):
    """테이블 형식으로 출력"""
    from rich.table import Table

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("상태", width=6)
    table.add_column("제목", width=40)
    table.add_column("발신자", width=25)
    table.add_column("날짜", width=15)

    for msg in messages:
        status_icons = []
        if msg.get("is_unread"):
            status_icons.append("🔴")
        if msg.get("is_starred"):
            status_icons.append("⭐")
        if msg.get("is_important"):
            status_icons.append("❗")

        status_str = " ".join(status_icons) if status_icons else "✅"

        # 텍스트 길이 제한
        subject = msg.get("subject", "(제목 없음)")
        if len(subject) > 37:
            subject = subject[:37] + "..."

        from_addr = msg.get("from", "Unknown")
        if len(from_addr) > 22:
            from_addr = from_addr[:22] + "..."

        table.add_row(status_str, subject, from_addr, _format_date(msg.get("date", "")))

    console.print()
    console.print(table)


def _format_date(date_str: str) -> str:
    """날짜 포맷팅"""
    if not date_str:
        return "Unknown"

    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%m/%d %H:%M")
    except Exception:
        # 파싱 실패 시 원본 문자열의 일부만 반환
        return date_str[:10] if len(date_str) > 10 else date_str


@gmail_app.command("search")
def gmail_search_command(
    search_term: str = typer.Argument(..., help="검색어"),
    max_results: int = typer.Option(10, "--max", "-m", help="최대 조회 개수"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """Gmail 이메일 검색"""

    async def _search_emails():
        try:
            console.print(f"🔍 '{search_term}' 검색 중...")

            client = await get_gmail_client()
            result = await client.search_messages(search_term, max_results)

            if json_output:
                from pyhub.mcptools.google.sheets.utils import json_dumps

                console.print(json_dumps(result))
            else:
                messages = result.get("messages", [])
                total_count = result.get("total_count", 0)

                console.print(f"✅ '{search_term}'에 대한 검색 결과: {total_count}개")

                if messages:
                    console.print("\n📋 검색 결과:")
                    for i, msg in enumerate(messages, 1):
                        console.print(f"  {i}. ID: {msg.get('id', 'Unknown')}")
                        console.print(f"     Thread ID: {msg.get('threadId', 'Unknown')}")

        except Exception as e:
            console.print(f"❌ 이메일 검색 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_search_emails())


@gmail_app.command("get")
def gmail_get_command(
    message_id: str = typer.Argument(..., help="이메일 메시지 ID"),
    include_body: bool = typer.Option(True, "--body/--no-body", help="이메일 본문 포함 여부"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """특정 Gmail 이메일 조회"""

    async def _get_message():
        try:
            console.print(f"📧 이메일 조회 중... (ID: {message_id})")

            client = await get_gmail_client()
            message = await client.get_message(message_id)

            if json_output:
                from pyhub.mcptools.google.sheets.utils import json_dumps

                if not include_body:
                    message.pop("body", None)
                console.print(json_dumps(message))
            else:
                console.print("✅ 이메일 정보:")
                console.print(f"  제목: {message.get('subject', 'No Subject')}")
                console.print(f"  발신자: {message.get('from', 'Unknown')}")
                console.print(f"  수신자: {message.get('to', 'Unknown')}")
                console.print(f"  날짜: {message.get('date', 'Unknown')}")
                console.print(f"  메시지 ID: {message.get('id', 'Unknown')}")
                console.print(f"  스레드 ID: {message.get('thread_id', 'Unknown')}")

                if include_body:
                    body = message.get("body", {})
                    if body.get("text"):
                        console.print(f"\n📄 본문 (텍스트):\n{body['text'][:500]}...")
                    elif body.get("html"):
                        console.print(f"\n📄 본문 (HTML):\n{body['html'][:500]}...")

        except Exception as e:
            console.print(f"❌ 이메일 조회 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_get_message())


@gmail_app.command("send")
def gmail_send_command(
    to: str = typer.Option(..., "--to", help="수신자 이메일 주소"),
    subject: str = typer.Option(..., "--subject", help="이메일 제목"),
    body: str = typer.Option(..., "--body", help="이메일 본문"),
    body_type: str = typer.Option("plain", "--type", help="본문 타입 (plain 또는 html)"),
    cc: str = typer.Option(None, "--cc", help="참조 이메일 주소"),
    bcc: str = typer.Option(None, "--bcc", help="숨은 참조 이메일 주소"),
):
    """Gmail 이메일 발송"""

    async def _send_email():
        try:
            console.print(f"📤 이메일 발송 중... (받는 사람: {to})")

            client = await get_gmail_client()
            result = await client.send_message(to=to, subject=subject, body=body, body_type=body_type, cc=cc, bcc=bcc)

            console.print("✅ 이메일이 성공적으로 발송되었습니다!")
            console.print(f"  메시지 ID: {result.get('id', 'Unknown')}")
            console.print(f"  수신자: {to}")
            console.print(f"  제목: {subject}")

        except Exception as e:
            console.print(f"❌ 이메일 발송 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_send_email())


@gmail_app.command("labels")
def gmail_labels_command(
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """Gmail 라벨 목록 조회"""

    async def _list_labels():
        try:
            console.print("🏷️ Gmail 라벨 목록 조회 중...")

            client = await get_gmail_client()
            result = await client.list_labels()

            if json_output:
                from pyhub.mcptools.google.sheets.utils import json_dumps

                console.print(json_dumps(result))
            else:
                labels = result.get("labels", [])
                total_count = result.get("total_count", 0)

                console.print(f"✅ 라벨 {total_count}개를 찾았습니다.")

                # 시스템 라벨과 사용자 라벨 분리
                system_labels = [l1 for l1 in labels if l1.get("type") == "system"]
                user_labels = [l2 for l2 in labels if l2.get("type") == "user"]

                if system_labels:
                    console.print("\n🔧 시스템 라벨:")
                    for label in system_labels:
                        console.print(f"  • {label.get('name', 'Unknown')} (ID: {label.get('id', 'Unknown')})")

                if user_labels:
                    console.print("\n👤 사용자 라벨:")
                    for label in user_labels:
                        console.print(f"  • {label.get('name', 'Unknown')} (ID: {label.get('id', 'Unknown')})")

        except Exception as e:
            console.print(f"❌ 라벨 목록 조회 실패: {e}")
            raise typer.Exit(1) from e

    asyncio.run(_list_labels())
