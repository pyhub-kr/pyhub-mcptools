import os
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import httpx
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn

from pyhub.mcptools.core.choices import OS


def download_update(version: str, target_dir: str = ".", verbose: bool = False) -> None:
    """새 버전을 다운로드하고 지정 경로에 압축을 풉니다."""

    # .github/workflows/release.yml 에서 명시한 파일명 포댓을 따릅니다.

    url = (
        f"https://github.com/pyhub-kr/pyhub-mcptools/releases/download/v{version}/"
        f"pyhub.mcptools-{OS.get_current_os_type()}-v{version}.zip"
    )
    if verbose:
        print("Download", url)

    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    temp_file_path = None

    try:
        # 임시 파일명 생성 (실제 파일은 아직 열지 않음)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
            temp_file_path = temp_file.name

        # 다운로드 (별도의 파일 핸들로 작업)
        with open(temp_file_path, "wb") as temp_file:
            with httpx.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                content_type = response.headers.get("content-type", "")

                if verbose:
                    print(f"Content-Type: {content_type}")

                # GitHub이 에러 페이지를 반환할 경우(HTML) 체크
                if "text/html" in content_type:
                    if verbose:
                        print("서버가 HTML을 반환했습니다. 유효한 ZIP 파일이 아닙니다.")
                    raise ValueError(
                        f"다운로드 실패: 서버가 ZIP 파일 대신 HTML을 반환했습니다. "
                        f"버전 {version}이 존재하지 않을 수 있습니다."
                    )

                with Progress(
                    TextColumn("[bold blue]다운로드 중..."),
                    BarColumn(),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                ) as progress:
                    task = progress.add_task("download", total=total)

                    for chunk in response.iter_bytes(chunk_size=8192):
                        temp_file.write(chunk)
                        progress.update(task, advance=len(chunk))

            # 파일을 닫고 flush 후 다음 작업 진행
            temp_file.flush()

        # 압축 파일 유효성 확인 (새로운 핸들로 열기)
        try:
            with zipfile.ZipFile(temp_file_path, "r") as zip_ref:
                # 파일 목록 확인만으로 유효성 검사
                file_list = zip_ref.namelist()
                if verbose:
                    print(f"ZIP 파일 검증 완료. {len(file_list)}개 파일 포함")

                # 압축 해제
                zip_ref.extractall(target_path)

            # zip_ref는 이 지점에서 명시적으로 닫힘 (with 블록 종료)

        except zipfile.BadZipFile as e:
            # 유효하지 않은 ZIP 파일
            if verbose:
                print(f"다운로드한 파일이 유효한 ZIP 형식이 아닙니다: {e}")
                if os.path.exists(temp_file_path):
                    print(f"다운로드한 파일 크기: {os.path.getsize(temp_file_path)} bytes")

            raise ValueError("다운로드한 파일이 유효한 ZIP 형식이 아닙니다") from e

    except httpx.RequestError as e:
        if verbose:
            print(f"다운로드 중 네트워크 오류 발생: {e}")
        raise ValueError("다운로드 중 오류가 발생했습니다") from e

    finally:
        # 임시 파일 정리 (재시도 로직 추가)
        if temp_file_path and os.path.exists(temp_file_path):
            for _ in range(5):  # 최대 5번 재시도
                try:
                    os.unlink(temp_file_path)
                    break
                except PermissionError:
                    if verbose:
                        print(f"임시 파일 삭제 재시도 중: {temp_file_path}")
                    time.sleep(0.5)  # 0.5초 대기 후 재시도
                except Exception as e:
                    if verbose:
                        print(f"임시 파일 삭제 중 오류: {e}")
                    break


def apply_update(version: str, verbose: bool) -> None:
    """기존 버전을 새 버전으로 교체합니다."""

    # 현재 실행 파일 경로
    current_exe = sys.executable
    app_dir = os.path.dirname(current_exe)
    current_os = OS.get_current()

    if verbose:
        print("current_exe :", current_exe)
        print("app_dir :", app_dir)

    # 임시 디렉토리 생성하고, 별도 스크립트 내에서 임시 폴더 제거
    with tempfile.TemporaryDirectory(delete=False) as temp_dir:
        temp_dir_path = Path(temp_dir)

        # 향상된 예외 처리
        try:
            download_update(version, temp_dir, verbose)
        except ValueError as e:
            print(f"[red]업데이트 다운로드 실패: {e}[/red]")
            return

        if current_os == OS.WINDOWS:
            script = rf"""
@echo off
setlocal

echo The update will be applied soon. Please wait a moment.
timeout /t 2 >nul

echo Removing previous version...
rd /s /q "{app_dir}\_internal"
del "{current_exe}"

echo Copying new version...
if exist "{temp_dir}\pyhub.mcptools\" (
    xcopy /s /e /y "{temp_dir}\pyhub.mcptools\*.*" "{app_dir}"  >nul
) else (
    xcopy /s /e /y "{temp_dir}\*.*" "{app_dir}" >nul
)

echo Removing temporary directory...
rd /s /q "{temp_dir}"

echo Update completed!
echo Press Enter to exit.
endlocal
            """
            if verbose:
                print("💻 [Update Script]")
                print("-" * 50)
                print(script)
                print("-" * 50)

            # 시스템 임시 디렉토리에 update.bat 생성
            # 윈도우에서는 실행 중인 BAT 스크립트에서 자기 자신 삭제를 허용하지 않음.
            # 그래서 temp_dir 경로가 아닌, 다른 경로에 update.bat 스크립트 생성
            system_temp = tempfile.gettempdir()
            script_path = Path(system_temp) / "pyhub_mcptools_update.bat"

            # 한글 윈도우에서는 디폴트 encoding=cp949. script는 영어로만 구성했기에
            # encoding 옵션은 적용하지 않아도 됩니다.
            script_path.write_text(script)
            subprocess.Popen(["cmd", "/c", script_path], shell=True)

        elif current_os == OS.MACOS:
            script = f"""#!/bin/bash

echo "The update will be applied soon. Please wait a moment."
sleep 2
echo "Removing previous version..."
rm -rf "{app_dir}/_internal"
rm "{current_exe}"

echo "Copying new version..."
# Need to copy contents of pyhub.mcptools folder after extraction
if [ -d "{temp_dir}/pyhub.mcptools" ]; then
    cp -R "{temp_dir}/pyhub.mcptools/"* "{app_dir}/"
else
    cp -R "{temp_dir}/"* "{app_dir}/"
fi

echo "Granting execute permission to {current_exe}"
chmod +x "{current_exe}"

echo "Removing temporary directory..."
rm -rf "{temp_dir}"

echo "Update completed!"
echo "Press Enter to exit..."
echo
"""
            if verbose:
                print("💻 [Update Script]")
                print("-" * 50)
                print(script)
                print("-" * 50)
            script_path = temp_dir_path / "update.sh"
            script_path.write_text(script)
            os.chmod(script_path, 0o755)
            subprocess.Popen(["bash", script_path])
