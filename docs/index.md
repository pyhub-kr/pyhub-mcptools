# 파이썬사랑방 MCP 도구

!!! note

    이 MCP 도구는 오픈소스로 개발되어 모든 코드가 [소스코드 저장소](https://github.com/pyhub-kr/pyhub-mcptools)에 공개되어 있습니다.
    사용자의 정보를 수집하거나 악의적인 코드가 포함되어 있지 않으니 안심하고 사용하실 수 있습니다.

## Videos

추가 툴 설치나 인증 과정도 없습니다. Microsoft 365 구독도 없어도 됩니다.
엑셀 정품 인증도 요구하지 않습니다.

편집이 가능한 엑셀 + Claude Desktop + "파이썬 사랑방 MCP 도구" 끝.

<div class="video-container">
    <iframe src="https://www.youtube.com/embed/MfPBhVPGz_4?si=zXk_m7HhIKCHeYmX" allowfullscreen></iframe>
</div>

## 지원 도구

### 엑셀 MCP 도구

Claude/Cursor와 함께 엑셀 화면을 같이 보며, 함께 읽고 수정할 수 있습니다.

!!! note

    열려진 엑셀 파일에 대해서만 지정 범위에 대해서 접근할 뿐, 파일 시스템을 탐색하지 않습니다.

[다른 엑셀 도구](https://github.com/negokaz/excel-mcp-server)는 엑셀 파일에 대한 읽고 쓰기를 지원합니다.
그래서 엑셀 프로그램이 없어도 수행이 가능하다는 장점이 있지만, 실시간으로 엑셀 프로그램의 변경사항을 감지할 수 없고
파일 단위로만 작업이 가능하다는 제한이 있어서 MCP와 동시에 같은 파일을 편집할 수는 없습니다.
그리고 DRM이 걸린 엑셀 파일에 대해서는 접근할 수 없습니다.

본 [엑셀 도구](./mcptools/excel/index.md)에서는 엑셀 프로그램과 직접 통신하는 방식을 사용하기 때문에,
사용자와 MCP가 동시에 같은 엑셀 파일을 실시간으로 편집할 수 있어 자연스럽고 효율적인 협업이 가능합니다.
DRM이 걸린 엑셀 문서도 엑셀 프로그램을 통해 열려있는 상황에서는 협업이 가능합니다.

<video width="100%" controls>
    <source src="./mcptools/excel/assets/pyhub.mcptools-v0.4.6.mp4" type="video/mp4">
</video>

## 설치 방법

파이썬사랑방 MCP 도구는 다음 2가지 방법으로 설치하실 수 있습니다.

1. 실행 파일 (exe) 버전
2. 소스 코드 버전

### 실행 파일 버전

+ ✅ 파이썬 설치가 필요 없이, 즉시 실행 가능
+ ✅ 파이썬 최신 버전 3.13 빌드 (보다 빠른 파이썬)
+ ✅ 별도의 의존성 설치가 필요 없음
+ ✅ 머신의 파이썬 개발환경으로부터 독립적인 실행
+ ✅ Claude 설정파일 자동 구성 지원
+ 😢 현재 실행 파일이 코드 서명되지 않아 Windows Defender나 다른 보안 프로그램에서 경고가 발생할 수 있음.

### 소스 코드 버전

+ ✅ 소스 코드를 직접 확인하고 수정 가능
+ ✅ 릴리즈 전에 최신 기능을 바로 사용 가능
+ 🤔 직접 파이썬 설치, 가상환경 구성, 의존성 팩키지 설치가 필요
+ 🤔 Claude 설정파일을 직접 구성해야 함
+ 😢 구성 과정에서 오류가 발생할 경우 직접 해결해야 함

## 지원 플랫폼

+ [윈도우 설치 방법](./setup/windows/index.md)
+ [macOS 설치 방법](./setup/macos/index.md)
