# 릴리즈 노트

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
