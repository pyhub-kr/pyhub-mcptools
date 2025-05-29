import os
import signal
import subprocess
from typing import List


class Sidecar:
    """
    Context manager to spawn one or more sidecar subprocesses and ensure
    they terminate when exiting the context, supporting Windows, macOS, and Linux.
    """

    def __init__(self, cmds: List[str]):
        """
        Args:
            cmds: 실행할 사이드카 명령들을 문자열 리스트로 전달합니다.
        """
        self.cmds = cmds
        self.procs: List[subprocess.Popen] = []
        self.is_windows = os.name == "nt"

    def __enter__(self) -> "Sidecar":
        errors = []
        # 각 명령어를 시도하고, 실패해도 다음 명령어를 시도합니다.
        for cmd_str in self.cmds:
            args = cmd_str.split()
            try:
                if self.is_windows:
                    proc = subprocess.Popen(
                        args,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                else:
                    proc = subprocess.Popen(
                        args,
                        preexec_fn=os.setsid,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                self.procs.append(proc)
            except FileNotFoundError as e:
                errors.append(e)
        # 모든 명령어 실행 후 에러가 발생했으면 첫 번째 FileNotFoundError를 발생시킵니다.
        if errors:
            raise errors[0]
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        for proc in self.procs:
            if not proc:
                continue
            try:
                if self.is_windows:
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                pass
        for proc in self.procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    if self.is_windows:
                        proc.kill()
                    else:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
