# 엑셀 도구

## 요구 사항

+ 엑셀 2016 이상
+ 윈도우/macOS 지원

## 지원 도구

### excel_get_opened_workbooks

Excel 프로그램에 열려있는 모든 워크북과 시트 내역 조회

### excel_get_values_from_active_sheet

Excel 프로그램에 열려있는 워크북에서 활성화된 시트 특정 범위의 데이터 조회. 범위를 지정하지 않으면 전체 범위.

### excel_get_values_from_sheet

Excel 프로그램에 열려있는 워크북에서 지정 시트 특정 범위의 데이터 조회. 범위를 지정하지 않으면 전체 범위.

### excel_set_values_to_active_sheet

Excel 프로그램에 열려있는 워크북에서 활성화된 시트의 지정된 범위에 데이터를 기록

### excel_set_values_to_sheet

Excel 프로그램에 열려있는 워크북의 지정 시트의 지정된 범위에 데이터를 기록

## 활용 예

!!! note

    각 대화에서 처음 사용하는 도구는 매번 허용해주셔야 합니다.

열려진 엑셀 파일 목록도 잘 조회하구요.

![](./assets/01-claude-mcp-1.png)

![](./assets/02-get-opened-workbooks.png)

지정 시트의 모든 값도 읽을 수 있고, 범위를 지정해서 읽을 수 있습니다.

![](./assets/03-get-values-from-active-sheet.png)

그리고, 원하는 좌표에 값을 기입할 수도 있습니다.

![](./assets/04-set-values-to-active-sheet.png)