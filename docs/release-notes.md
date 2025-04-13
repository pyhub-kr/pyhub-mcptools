# 릴리즈 노트

## v0.7.5

+ `run_sse_proxy` 명령에서 SSE 서버 접속 실패에 대한 오류 처리

## v0.7.4

+ `setup-add` 명령
    - `--dry` 옵션 지원 : 설정 적용없이 출력
    - `--environment`, `-e` 옵션 지원 : 설정에 환경변수 추가
+ `log-tail`, `log-folder` 명령 추가 : 로그 모니터링
+ SSE 서버 지원 강화
    - `run-sse-proxy` 명령 지원 : SSE 서버와의 STDIO 방식으로 프록시 지원 (Claude Desktop에서는 STDIO 방식만 지원)
    - `setup-add --transport sse` 명령에서 `run-sse-proxy` 명령 지원
    - SSE 서버 구동에서 `django ASGI` 서버 구동

## v0.7.3

+ `update` 명령에서 Claude Desktop 앱에 한해서만 강제 종료 수행여부 확인

## v0.7.2

+ `excel_get_opened_workbooks` 도구에서 워크북 이름, 시트 이름에 대한 한글 자소 분리 대응
+ `excel_get_values` 도구의 응답 포맷을 JSON에서 CSV로 변경
+ `release-note` 명령 추가 : 웹페이지를 방문하지 않아도 콘솔에서 릴리즈 노트 즉시 확인 가능

## v0.7.1

+ 엑셀 도구. 차트 도구 릴리즈

## v0.7.0

+ macOS : 엑셀 자동화 권한 문제 해결

## v0.6.7

+ `excel_set_values` 도구에 `autofit` 인자 지원 추가 (디폴트: False) : 자동 맞춤 기능
+ `excel_autofit` 도구 추가
+ `excel_get_valuess`, `excel_autofit` 도구에 `expand_mode` 인자 추가 (table, right, down)
+ `setup-add` 명령에서 Cursor 설정 지원 (only 윈도우)
+ MCP 도구 등록 장식자에 실험실 `experimental` 인자를 추가하여, 실험적 도구는 별도 플래그를 통해서만 활성화
+ 멜론 노래 검색 도구 추가 (실험실)

## v0.6.6

+ `update` 명령에서 Claude Desktop, Cursor 종료 여부를 묻는 기능이 추가되었습니다.

## v0.6.5

+ `excel_set_formula` Tool 추가 : 엑셀 수식 지원
+ `setup-add` 명령에 Claude 설정명 인자 (`--config-name`) 지원

## v0.6.3

+ `setup-add` 명령에서 Claude Desktop 미설치 상황에 대한 안내 메시지 추가

## v0.6.2

+ 엑셀 도구, 시트 추가 도구 지원 : `excel_add_sheet`
+ `update` 명령에서 http 요청 라이브러리를 `httpx`로 변경

## v0.6.1

+ `update` 명령을 통한 업데이트 지원
