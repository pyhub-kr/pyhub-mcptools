# 감정 분석 도구

LLM 없이 규칙 기반으로 텍스트의 감정을 분석하는 도구입니다. 한국어와 영어를 지원하며, 긍정/부정/중립 감정을 판별합니다.

## 주요 기능

- **언어 지원**: 한국어, 영어
- **감정 분류**: 긍정(positive), 부정(negative), 중립(neutral)
- **신뢰도 점수**: 0-1 사이의 확신도
- **키워드 추출**: 주요 감정 단어 식별
- **부정어 처리**: "안 좋아요" → 부정
- **강조어 처리**: "매우 좋아요" → 강한 긍정

## 기술적 특징

- **한국어**: 사전 기반 접근 (내장 감정 사전)
- **영어**: VADER 감정 분석기 (선택적 설치)
- **오프라인 동작**: 인터넷 연결 불필요
- **빠른 처리**: LLM 대비 매우 빠른 속도

## 사용 예시

### 단일 텍스트 분석

```python
# 한국어
result = await sentiment_analyze(
    text="정말 좋아요! 최고입니다",
    language="ko"
)
# 결과: {"sentiment": "positive", "confidence": 0.96, ...}

# 영어 (VADER 설치 시)
result = await sentiment_analyze(
    text="This is amazing!",
    language="en"
)

# 자동 언어 감지
result = await sentiment_analyze(
    text="너무 실망했어요",
    language="auto"
)
```

### 배치 분석

```python
results = await sentiment_analyze_batch(
    texts=["좋아요", "싫어요", "보통이에요"],
    language="ko"
)
```

## 설치

### 기본 설치 (한국어만)
```bash
pip install pyhub-mcptools
```

### 영어 지원 추가
```bash
pip install "pyhub-mcptools[sentiment]"
```

## 도구 목록

### sentiment_analyze

단일 텍스트의 감정을 분석합니다.

**매개변수:**
- `text`: 분석할 텍스트
- `language`: 언어 설정 ("auto", "en", "ko")

**반환값:**
```json
{
    "sentiment": "positive",
    "confidence": 0.85,
    "scores": {
        "positive": 0.85,
        "negative": 0.10,
        "neutral": 0.05
    },
    "keywords": ["좋", "최고"],
    "language": "ko"
}
```

### sentiment_analyze_batch

여러 텍스트를 한 번에 분석합니다.

**매개변수:**
- `texts`: 텍스트 리스트
- `language`: 언어 설정

**반환값:**
각 텍스트에 대한 분석 결과 리스트

## 한계점

- **문맥 이해 부족**: 복잡한 문맥이나 아이러니 감지 어려움
- **도메인 특화 부족**: 일반적인 감정 표현 위주
- **형태소 분석 없음**: 한국어는 어절 단위 매칭
- **이모티콘 제한**: 기본 이모티콘만 부분 지원

## 활용 사례

- 고객 리뷰 감정 분석
- SNS 게시물 감정 모니터링
- 챗봇 대화 감정 인식
- 실시간 피드백 분석