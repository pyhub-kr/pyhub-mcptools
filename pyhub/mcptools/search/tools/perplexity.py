import json

import httpx
from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.types import PyHubTextChoices

# Prices : https://docs.perplexity.ai/guides/pricing#non-reasoning-models


class RecencyChoices(PyHubTextChoices):
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
    recency: str = Field(
        default=RecencyChoices.get_none_value(),
        description=RecencyChoices.get_description("Time filter for search results"),
    ),
    search_domain_allow_list: str = Field(
        default="",
        description="""List of domains to specifically include in the search (comma-separated).
            Only results from these domains will be considered.""",
        examples=["wikipedia.org,python.org", "django-htmx.readthedocs.io"],
    ),
    search_domain_disallow_list: str = Field(
        default="",
        description="""List of domains to exclude from the search (comma-separated).
            Results from these domains will be filtered out.""",
        examples=["pinterest.com,quora.com", "reddit.com"],
    ),
) -> str:
    """Performs an AI-powered web search using Perplexity AI.

    This tool leverages Perplexity AI's API to perform intelligent web searches,
    providing accurate and reliable information through AI-powered search and
    verification across multiple sources.

    Returns:
        str: A JSON-encoded string containing the search results and any relevant citations.
    """

    url = "https://api.perplexity.ai/chat/completions"

    model = settings.PERPLEXITY_MODEL
    api_key = settings.PERPLEXITY_API_KEY
    max_tokens = settings.PERPLEXITY_MAX_TOKENS
    temperature = settings.PERPLEXITY_TEMPERATURE
    search_context_size = settings.PERPLEXITY_SEARCH_CONTEXT_SIZE

    system_prompt = "Be precise and concise."

    search_domain_filter = []

    if search_domain_allow_list:
        search_domain_allow_list: list[str] = search_domain_allow_list.split(",")
        search_domain_filter.extend(search_domain_allow_list)

    if search_domain_disallow_list:
        search_domain_disallow_list: list[str] = search_domain_disallow_list.split(",")
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
