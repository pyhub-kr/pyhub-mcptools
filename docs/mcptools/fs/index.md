# 파일시스템 도구

`FS_LOCAL_HOME` 환경변수가 지정되면 파일시스템 도구가 활성화됩니다.

## 활용 스크린샷

![](./assets/virtual-students-csv-data.png#noborder)

## 관련 환경변수

1. `FS_LOCAL_HOME` : 디폴트 `None`
2. `FS_LOCAL_ALLOWED_DIRECTORIES` : 디폴트 빈 리스트

``` json title="적용 예시"
"env": {
    "FS_LOCAL_HOME": "~/mcptools/files/"
}
```


## 지원 도구

모두 `FS_LOCAL_HOME`와 `FS_LOCAL_ALLOWED_DIRECTORIES` 환경변수에 지정된 경로에 대해서만 동작하며, 그 외의 경로에 대해서는 요청을 거부합니다.

1. `fs__read_file` : 1개 파일 내용 읽기
2. `fs__read_multiple_files` : 다수 파일 내용 읽기 
3. `fs__write_file` : 1개 텍스트 파일 생성
4. `fs__edit_file` : 1개 텍스트 파일 수정
5. `fs__create_directory` : 1개 디렉토리 생성
6. `fs__list_directory` : 디렉토리 내역 (재귀 지원)
7. `fs__move_file` : 1개 파일 이동
8. `fs__find_files` : 지정 경로에서 파일 찾기
9. `fs__get_file_info` : 1개 파일 세부 내역 조회
10. `fs__list_allowed_directories` : 허용된 디렉토리 목록 조회
