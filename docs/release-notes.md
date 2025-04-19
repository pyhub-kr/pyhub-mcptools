# 릴리즈 노트

## How to update

[릴리즈 페이지](https://github.com/pyhub-kr/pyhub-mcptools/releases/)에서 최신 버전을 다운받으실 수 있습니다. 설치 방법은 아래 문서를 참고해주세요.

+ [윈도우에서 설치하기](./setup/windows/index.md)
+ [macOS에서 설치하기](./setup/macos/index.md)

이미 `pyhub.mcptools`가 설치되어있으시다면, 설치 경로에서 `update` 명령으로 최신 버전으로 업데이트하실 수 있습니다.

```
pyhub.mcptools update
```

## v0.9.3

+ 간략하게 `pyhub.mcptools` 외에 `mcptools` 동일한 명령 추가

## v0.9.2

+ 피벗 테이블 생성/조회/삭제 도구 추가 지원
+ 테이블 변환 도구 추가 지원

## v0.9.1

+ Cursor MCP 안정성 개선

## v0.9.0

+ Cursor MCP 호환성 테스트 완료

## v0.8.8

+ (윈도우 전용) `excel_get_special_cells_address` 도구 지원
    - 다양한 조건(빈 셀, 코멘트 셀, 상수 셀, 수식 셀, 최근 사용했던 셀 등)을 셀을 빠르게 찾아냅니다.

## v0.8.6

+ `excel_set_styles` 도구 지원
    - 셀 배경색, 글자색, 볼드, 이탤릭 스타일 변경 지원
    - 윈도우 전용 : 취소선, 밑선, 좌우/상하 정렬 지원
    - 스타일 리셋 지원

## v0.8.5

+ `setup-add` 명령에서 Claude Desktop, Cursor, Windsurf 설정 지원

## v0.8.4

+ [엑셀 도구](./mcptools/excel/index.md)에서 유저가 전달한 CSV 파일 읽기 지원
    - 먼저 [파일시스템 도구](./mcptools/fs/index.md)를 활성화시켜주셔야 합니다.

## v0.8.3

+ [네이버 길찾기 도구](./mcptools/maps/index.md) 지원

## v0.8.2

+ `settings.FS_LOCAL_ALLOWED_DIRECTORIES` 오타 수정

## v0.8.1

+ MCP 설정의 [환경변수 조회/추가/제거 명령 지원](./setup/env/index.md)

## v0.8.0

+ 파일시스템 도구 추가 : `FS_LOCAL_HOME` 환경변수가 지정되면 자동 활성화

## v0.7.10

+ `ONLY_EXPOSE_TOOLS` 환경변수를 통해 지정 패턴의 도구만 노출

!!! note

    [환경변수 설정법](./setup/env.md)

## v0.7.9

+ [퍼플렉시티 검색 도구 추가](./mcptools/search/perplexity.md)

## v0.7.8

+ 차트 생성 시에 Claude Desktop 애플리케이션이 죽는 버그 해결 : TextChoices로 생성한 타입에 대해서 Optional을 지정하지 않으면, Claude Desktop이 죽는 데 로그도 남기지 않네요. :-(

## v0.7.7

+ `excel_find_data_ranges` 도구 추가 : 지정 시트에서 각 데이터의 범위 목록을 반환
    - 이제 데이터 위치를 찾기 위해서 Claude에서 일일이 시트값을 읽어 조회하지 않아도 됩니다. 

## v0.7.6

+ `excel_set_values` 도구에서 CSV 포맷 응답을 지원하여, 엑셀 호환성 개선 

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
