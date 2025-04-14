import json
from typing import Optional

import httpx
from django.conf import settings
from django.db.models import TextChoices
from pydantic import Field

from pyhub.mcptools import mcp

# Prices : https://docs.perplexity.ai/guides/pricing#non-reasoning-models


class RecencyChoices(TextChoices):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


ENABLED_PERPLEXITY_TOOLS = settings.PERPLEXITY_API_KEY is not None


@mcp.tool(enabled=ENABLED_PERPLEXITY_TOOLS)
async def search__perplexity(
    query: str = Field(
        description="""The search query to be processed by Perplexity AI.

        Guidelines for effective queries:
        1. Be specific and contextual: Add 2-3 extra words of context
        2. Use search-friendly terms that experts would use
        3. Include relevant context but keep it concise
        4. Avoid few-shot prompting or example-based queries

        Good examples:
        - "Analyze the impact of Fed interest rate decisions on KOSPI market in 2024"
        - "Compare South Korea's inflation rate trends with other OECD countries in 2023-2024"
        - "Explain recent changes in Korean real estate market regulations and their effects"

        Poor examples:
        - "Tell me about stocks"
        - "What is inflation?"
        - "How's the economy doing?"
        """,
        examples=[
            "Explain the correlation between US Treasury yields and Korean bond markets in 2024",
            "Compare investment strategies for Korean retail investors during high inflation periods",
        ],
    ),
    recency: Optional[RecencyChoices] = Field(
        default=None,
        description="""Time filter for search results. Options:
            - "hour": Results from the last hour
            - "day": Results from the last day
            - "week": Results from the last week
            - "month": Results from the last month""",
        examples=["day", "week"],
    ),
    search_domain_allow_list: Optional[list[str]] = Field(
        default=None,
        description="""List of domains to specifically include in the search.
            Only results from these domains will be considered.""",
        examples=[["wikipedia.org", "python.org"], ["django-htmx.readthedocs.io"]],
    ),
    search_domain_disallow_list: Optional[list[str]] = Field(
        default=None,
        description="""List of domains to exclude from the search.
            Results from these domains will be filtered out.""",
        examples=[["pinterest.com", "quora.com"], ["reddit.com"]],
    ),
) -> str:
    """Performs an AI-powered web search using Perplexity AI.

    This tool uses Perplexity AI's API to perform intelligent web searches with
    natural language processing capabilities. It excels at finding accurate and
    reliable information by leveraging AI-powered search and verification across
    multiple sources. It can filter results by recency and specific domains,
    making it useful for targeted research, fact-checking, and gathering up-to-date
    information from trusted sources.

    Query Guidelines:
        1. Be Specific and Contextual:
           - Add 2-3 extra words of context for better results
           - Example: "Analyze Bank of Korea's monetary policy impact on SMEs in 2024"

        2. Use Search-Friendly Terms:
           - Use technical terms and specific concepts
           - Consider how experts would describe the topic
           - Example: "Compare yield curve trends between Korean and US government bonds"

        3. Include Relevant Context:
           - Add timeframes, market conditions, or specific sectors
           - Keep queries focused and concise
           - Example: "Evaluate Korean semiconductor industry export trends amid US-China tensions"

        4. Avoid:
           - Generic questions without context
           - Few-shot prompting with examples
           - Multiple unrelated questions in one query

        5. Missing Context Checklist:
           If your query seems too broad, consider adding information about:
           - Specific time periods or market conditions
           - Geographic regions or markets
           - Economic indicators or metrics
           - Industry sectors or company types
           - Policy or regulatory context

    Returns:
        str: A JSON-encoded string containing the search results and any relevant citations.
            The response includes the AI-generated answer and source URLs.

    Examples:
        >>> search__perplexity(
        ...     "Compare Django's class-based views vs function-based views for REST API development"
        ... )
        >>> search__perplexity(
        ...     "Explain Django's database connection pooling strategies for high-traffic sites",
        ...     recency="week",
        ...     search_domain_allow_list=["docs.djangoproject.com", "django-developers.googlegroups.com"]
        ... )
        >>> search__perplexity(
        ...     "Analyze Django REST Framework's pagination performance for large datasets",
        ...     search_domain_disallow_list=["medium.com", "dev.to"]
        ... )
    """

    #     # Add query quality check
    #     min_words = 6  # Minimum recommended words for a good query
    #     words = query.split()
    #
    #     if len(words) < min_words:
    #         suggestions = [
    #             "시간적 맥락 (예: 2024년 1분기, 최근 6개월)",
    #             "지역/시장 정보 (예: 국내 시장, 아시아 시장)",
    #             "산업 분야 (예: 반도체 산업, 금융 서비스)",
    #             "경제 지표 (예: 물가상승률, 실업률, GDP 성장률)",
    #             "정책적 맥락 (예: 금리 정책, 부동산 규제)",
    #         ]
    #         suggestion_text = "\n".join(f"- {s}" for s in suggestions)
    #         return f"""검색어가 너무 간단합니다. 더 나은 검색 결과를 위해 다음과 같은 정보를 추가해주세요:
    #
    # {suggestion_text}
    #
    # 현재 검색어: "{query}"
    #
    # 예시:
    # - "2024년 한국은행 기준금리 인상이 가계부채에 미치는 영향"
    # - "최근 6개월간 코스피 상장기업 실적 동향과 전망"
    # - "미국 인플레이션 둔화가 한국 수출기업에 미치는 영향 분석"
    #     """

    url = "https://api.perplexity.ai/chat/completions"

    model = settings.PERPLEXITY_MODEL
    api_key = settings.PERPLEXITY_API_KEY
    max_tokens = settings.PERPLEXITY_MAX_TOKENS
    temperature = settings.PERPLEXITY_TEMPERATURE
    search_context_size = settings.PERPLEXITY_SEARCH_CONTEXT_SIZE

    system_prompt = "Be precise and concise."

    search_domain_filter = []

    if search_domain_allow_list:
        search_domain_filter.extend(search_domain_allow_list)

    if search_domain_disallow_list:
        search_domain_filter.extend(f"-{domain}" for domain in search_domain_disallow_list)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "search_recency_filter": recency,
        # "top_p": 0.9,
        # "top_k": 0,
        # "return_images": False,
        # "return_related_questions": False,
        # https://docs.perplexity.ai/guides/search-domain-filters
        #  ex) white list - ["nasa.gov", "wikipedia.org", "space.com"]
        #  ex) black list - ["-pinterest.com", "-reddit.com", "-quora.com"]
        "search_domain_filter": search_domain_filter,
        # "presence_penalty": 0,
        # "frequency_penalty": 1,
        "web_search_options": {"search_context_size": search_context_size},
        # "response_format": {},  # 출력 포맷을 JSON으로 지정
        "stream": True,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    ai_message = ""

    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            citations = set()

            # 첫 번째 응답에서 id와 model 추출
            meta_info = {"input_tokens": 0, "output_tokens": 0}

            async for line in response.aiter_lines():
                if line := line.strip():
                    if line.startswith("data:"):
                        json_str = line[5:].strip()  # Remove 'data: ' prefix

                        try:
                            data = json.loads(json_str)

                            meta_info["id"] = data.get("id")
                            meta_info["model"] = data.get("model")

                            if "usage" in data:
                                meta_info["input_tokens"] = data["usage"]["prompt_tokens"]
                                meta_info["output_tokens"] += data["usage"]["completion_tokens"]

                            if "choices" in data:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    ai_message += delta["content"]
                            if "citations" in data:
                                citations.update(data["citations"])
                        except json.JSONDecodeError:
                            continue

            if citations:
                formatted_citations = "\n\n" + "\n".join(f"[{i + 1}] {url}" for i, url in enumerate(citations))
                ai_message += formatted_citations

    # return json.dumps(
    #     {
    #         "result": ai_message,
    #         # "id": meta_info.get("id"),
    #         # "model": meta_info.get("model"),
    #         # "usage": {
    #         #     "input_tokens": meta_info.get("input_tokens"),
    #         #     "output_tokens": meta_info.get("output_tokens"),
    #         # },
    #         # "search_context_size": search_context_size,
    #     }
    # )

    return ai_message
