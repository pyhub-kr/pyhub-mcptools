# 지원 환경변수

## JSON 설정

Claude Desktop 등의 MCP 호스트에서는 JSON 설정에서 `"env"` 키로 환경변수를 설정할 수 있습니다.

## 지정 이름 패턴의 도구만 노출하기

`ONLY_EXPOSE_TOOLS`

예시

+ 미지정 : 모든 도구가 노출
+ `"excel_.+"` : 모든 엑셀 도구만 노출
+ `"search_perplexity"` : `search_perplexity` 도구만 노출
+ + `"excel_.+,search_perplexity"` : 모든 엑셀 도구와 `search_perplexity` 도구만 노출 (콤마(`,`)로 여러 값을 구별합니다.)

``` json
"env": {
  "ONLY_EXPOSE_TOOLS": "search_.+"
}
```

---

정리 중
