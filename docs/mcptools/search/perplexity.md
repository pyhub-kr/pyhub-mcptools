# 퍼플렉시티 도구

[퍼플렉시티 API](https://docs.perplexity.ai/home)를 활용한 검색 도구를 지원합니다.

## 환경변수

환경변수를 통해 옵션을 변경하실 수 있습니다.

``` json hl_lines="9 10 11"
{
    "mcpServers": {
        "pyhub.mcptools": {
            "command": "c:\\mcptools\\pyhub.mcptools\\pythu.mcptools.exe",
            "args": [
                "run",
                "stdio"
            ],
            "env": {
                "PERPLEXITY_API_KEY": "pplx-여러분들의-Key를-지정해주세요-"
            }
        }
    }
}
```

!!! note

    "env" 키를 추가할 때, 콤마(`,`) 추가 등의 JSON 문법에 유의하세요.

### API KEY

`PERPLEXITY_API_KEY`

퍼플렉시티 API 사용을 위해 반드시 지정해주셔야 합니다.
이 **환경변수를 지정하셔야만 "퍼플렉시티 도구"가 활성화**됩니다.
[https://www.perplexity.ai/account/api](https://www.perplexity.ai/account/api) 페이지에서 발급받으실 수 있습니다.
신용카드 등록 및 크레딧 구매가 필요합니다.

### 온도

`PERPLEXITY_TEMPERATURE` : 디폴트 `0.2`

### 시스템 프롬프트

`PERPLEXITY_SYSTEM_PROMPT`

```
You are a helpful AI assistant.

Rules:
1. Provide only the final answer. It is important that you do not include any explanation on the steps below.
2. Do not show the intermediate steps information.

Steps:
1. Decide if the answer should be a brief sentence or a list of suggestions.
2. If it is a list of suggestions, first, write a brief and natural introduction based on the original query.
3. Followed by a list of suggestions, each suggestion should be split by two newlines.
```

공식문서 : [https://docs.perplexity.ai/guides/prompt-guide](https://docs.perplexity.ai/guides/prompt-guide)

### 검색 모델

`PERPLEXITY_MODEL` : 디폴트 `"sonar"`

공식문서 : [https://docs.perplexity.ai/guides/model-cards](https://docs.perplexity.ai/guides/model-cards)

### 생성 최대 토큰 수

`PERPLEXITY_MAX_TOKENS` : 디폴트 `1024`

### 생성 Context 크기

`PERPLEXITY_SEARCH_CONTEXT_SIZE` : 디폴트 `"low"` (`low`, `medium`, `high` 중 택일)

!!! note

    `low`, `medium`, `high` 옵션을 지원하며, Input/Output 토큰 가격은 동일하지만
    요청 1000개당 가격이 다릅니다. `sonar` 모델 기준으로 $5, $8, $12 입니다.

    공식문서 : [https://docs.perplexity.ai/guides/pricing#non-reasoning-models](https://docs.perplexity.ai/guides/pricing#non-reasoning-models)
