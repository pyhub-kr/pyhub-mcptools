import yfinance as yf
from pydantic import Field

from pyhub.mcptools import mcp

"""
yahoo_finance 주요 기능

+ 주식 정보 조회: 개별 주식의 과거 가격 데이터, 배당금 정보, 분할 정보 등을 조회할 수 있습니다.
+ 금융 데이터 다운로드: 일별, 주별, 월별 시계열 데이터를 Pandas DataFrame 형태로 쉽게 다운로드할 수 있습니다.
+ 다양한 금융 지표 제공: 시가, 고가, 저가, 종가, 거래량 등 주식 시장의 다양한 지표를 제공합니다.
+ 복수 종목 데이터 동시 조회: 여러 주식 종목의 데이터를 한 번에 조회하는 기능을 지원합니다.
"""


@mcp.tool()
async def search_yahoo_finance__historical_price(
    ticker: str = Field(
        examples=["AAPL"],
    ),
    period: str = Field(
        description="데이터 조회 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)",
        examples=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
    ),
    interval: str = Field(
        description="데이터 간격 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)",
        examples=["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
    ),
) -> str:
    """특정 주식의 지난 기간(예: 6개월) 동안의 일별 가격 데이터를 반환합니다."""
    try:
        # yfinance Ticker 객체 생성
        stock = yf.Ticker(ticker)

        # 히스토리 데이터 조회
        hist = stock.history(period=period, interval=interval)

        if hist.empty:
            return f"No historical data found for {ticker}"

        # 데이터 포맷팅
        result = [
            f"Historical price data for {ticker} ({period}, {interval} interval):\n",
            "Date | Open | High | Low | Close | Volume",
        ]

        # 최근 10개 데이터만 포함
        for date, row in list(hist.iterrows())[-10:]:
            result.append(
                f"{date.strftime('%Y-%m-%d')} | "
                f"{row['Open']:.2f} | {row['High']:.2f} | "
                f"{row['Low']:.2f} | {row['Close']:.2f} | "
                f"{int(row['Volume']):,}"
            )

        return "\n".join(result)

    except Exception as e:
        return f"Error fetching data for {ticker}: {str(e)}"


@mcp.tool()
async def search_yahoo_finance__quarterly_balance_sheet(
    ticker: str = Field(
        examples=["MSFT"],
    ),
) -> str:
    """지정된 기업의 분기별 대차대조표 데이터를 반환합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용한 분기별 대차대조표 조회 코드를 추가합니다.
    return "Quarterly balance sheet data for " + ticker


@mcp.tool()
async def search_yahoo_finance__performance_metrics(
    ticker: str = Field(
        description="주식 종목 심볼 (예: TSLA, AAPL)",
        examples=["TSLA"],
    ),
) -> str:
    """지정된 주식의 주요 재무 성과 지표 데이터를 반환합니다."""
    try:
        # yfinance Ticker 객체 생성
        stock = yf.Ticker(ticker)

        # 주요 정보 조회
        info = stock.info
        if not info:
            return f"No performance metrics found for {ticker}"

        # 주요 지표 정의
        metrics = {
            "Market Metrics": [
                ("marketCap", "시가총액", lambda x: f"${x/1e9:.2f}B"),
                ("volume", "거래량", lambda x: f"{x:,}"),
                ("averageVolume", "평균 거래량", lambda x: f"{x:,}"),
                ("fiftyTwoWeekHigh", "52주 최고가", lambda x: f"${x:.2f}"),
                ("fiftyTwoWeekLow", "52주 최저가", lambda x: f"${x:.2f}"),
            ],
            "Valuation Metrics": [
                ("trailingPE", "P/E (TTM)", lambda x: f"{x:.2f}"),
                ("forwardPE", "예상 P/E", lambda x: f"{x:.2f}"),
                ("priceToBook", "P/B", lambda x: f"{x:.2f}"),
                ("enterpriseToEbitda", "EV/EBITDA", lambda x: f"{x:.2f}"),
            ],
            "Financial Metrics": [
                ("returnOnEquity", "ROE", lambda x: f"{x*100:.2f}%"),
                ("returnOnAssets", "ROA", lambda x: f"{x*100:.2f}%"),
                ("profitMargins", "순이익률", lambda x: f"{x*100:.2f}%"),
                ("operatingMargins", "영업이익률", lambda x: f"{x*100:.2f}%"),
            ],
            "Growth & Dividend": [
                ("revenueGrowth", "매출 성장률", lambda x: f"{x*100:.2f}%"),
                ("earningsGrowth", "순이익 성장률", lambda x: f"{x*100:.2f}%"),
                ("dividendRate", "연간 배당금", lambda x: f"${x:.2f}"),
                ("dividendYield", "배당수익률", lambda x: f"{x*100:.2f}%"),
            ],
        }

        # 결과 포맷팅
        result = [f"\nPerformance Metrics for {ticker} ({info.get('longName', '')})\n"]

        # 현재 주가 정보 추가
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if current_price:
            result.append(f"Current Price: ${current_price:.2f}")

        # 카테고리별 지표 추가
        for category, category_metrics in metrics.items():
            result.append(f"\n{category}:")
            result.append("-" * 40)

            for key, label, formatter in category_metrics:
                if key in info and info[key] is not None:
                    try:
                        formatted_value = formatter(info[key])
                        result.append(f"{label}: {formatted_value}")
                    except (TypeError, ValueError):
                        continue

        # 애널리스트 추천 정보 추가
        if "recommendationMean" in info and info["recommendationMean"]:
            result.append("\nAnalyst Recommendations:")
            result.append("-" * 40)
            result.append(f"평균 추천등급 (1=강력매수, 5=강력매도): {info['recommendationMean']:.2f}")

        return "\n".join(result)

    except Exception as e:
        return f"Error fetching performance metrics for {ticker}: {str(e)}"


@mcp.tool()
async def search_yahoo_finance__quarterly_income_trend(
    tickers: list = Field(
        examples=[["AMZN", "GOOGL"]],
    ),
) -> str:
    """여러 기업의 분기별 손익계산서 데이터를 비교 분석하여 반환합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용한 분기별 손익계산서 조회 및 비교 코드를 추가합니다.
    return "Quarterly income trend analysis for: " + ", ".join(tickers)


@mcp.tool()
async def search_yahoo_finance__annual_cash_flow(
    ticker: str = Field(
        examples=["NVDA"],
    ),
) -> str:
    """지정된 기업의 연간 현금 흐름 데이터를 반환합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용한 연간 현금 흐름 데이터 조회 코드를 추가합니다.
    return "Annual cash flow data for " + ticker


@mcp.tool()
async def search_yahoo_finance__latest_news(
    ticker: str = Field(
        examples=["META"],
    ),
    count: int = Field(
        examples=[5],
    ),
) -> str:
    """지정된 기업에 대한 최신 뉴스 기사들을 반환합니다."""
    # 여기에 Yahoo Finance 라이브러리나 뉴스 API를 이용한 뉴스 기사 조회 코드를 추가합니다.
    return "Latest news for " + ticker


@mcp.tool()
async def search_yahoo_finance__institutional_holders(
    ticker: str = Field(
        examples=["AAPL"],
    ),
) -> str:
    """지정된 주식의 기관 투자자 보유 현황 데이터를 반환합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용한 기관 투자자 보유 현황 조회 코드를 추가합니다.
    return "Institutional holders for " + ticker


@mcp.tool()
async def search_yahoo_finance__insider_trading(
    ticker: str = Field(
        examples=["TSLA"],
    ),
    period: str = Field(
        default="3mo",
        examples=["3mo"],
    ),
) -> str:
    """지정된 주식의 최근 내부자 거래 데이터를 반환합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용한 내부자 거래 데이터 조회 코드를 추가합니다.
    return "Insider trading data for " + ticker


@mcp.tool()
async def search_yahoo_finance__options_chain(
    ticker: str = Field(
        examples=["SPY"],
    ),
    expiration_date: str = Field(
        examples=["2024-06-21"],
    ),
    option_type: str = Field(
        examples=["call"],
    ),
) -> str:
    """지정된 주식의 옵션 체인 데이터를, 만기일 및 옵션 유형에 따라 반환합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용한 옵션 체인 데이터 조회 코드를 추가합니다.
    return f"Options chain for {ticker} with expiration {expiration_date} and type {option_type}"


@mcp.tool()
async def search_yahoo_finance__analyst_recommendations(
    ticker: str = Field(
        examples=["AMZN"],
    ),
    period: str = Field(
        default="3mo",
        examples=["3mo"],
    ),
) -> str:
    """지정된 주식의 애널리스트 추천 정보를, 기간별로 반환합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용한 애널리스트 추천 정보 조회 코드를 추가합니다.
    return "Analyst recommendations for " + ticker


@mcp.tool()
async def search_yahoo_finance__comprehensive_financial_report(
    ticker: str = Field(
        examples=["MSFT"],
    ),
) -> str:
    """최신 분기 재무제표를 기반으로 지정된 기업의 종합 재무 건전성 리포트를 생성합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용하여 종합 재무 건전성 리포트 생성을 위한 코드를 추가합니다.
    return "Comprehensive financial health report for " + ticker


@mcp.tool()
async def search_yahoo_finance__dividend_split_comparison(
    ticker1: str = Field(
        examples=["KO"],
    ),
    ticker2: str = Field(
        examples=["PEP"],
    ),
) -> str:
    """두 기업의 배당 내역 및 주식 분할 정보를 비교 분석하여 반환합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용한 배당 및 주식 분할 내역 비교 코드를 추가합니다.
    return f"Dividend and stock split comparison between {ticker1} and {ticker2}"


@mcp.tool()
async def search_yahoo_finance__institutional_ownership_change(
    ticker: str = Field(
        examples=["TSLA"],
    ),
    period: str = Field(
        default="1y",
        examples=["1y"],
    ),
) -> str:
    """지정된 기업의 기관 투자자 소유 변화 추이를 분석하여 반환합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용한 기관 소유 변화 분석 코드를 추가합니다.
    return f"Institutional ownership change analysis for {ticker} over {period}"


@mcp.tool()
async def search_yahoo_finance__options_market_report(
    ticker: str = Field(
        examples=["AAPL"],
    ),
    time_to_expiration: int = Field(
        examples=[30],
    ),
) -> str:
    """지정된 주식의 단기 옵션 시장 활동을 분석한 보고서를 생성합니다."""
    # 여기에 Yahoo Finance 라이브러리를 이용한 옵션 시장 활동 보고서 생성 코드를 추가합니다.
    return f"Options market activity report for {ticker} with {time_to_expiration} days to expiration"


@mcp.tool()
async def search_yahoo_finance__tech_sector_analyst_summary(
    period: str = Field(
        default="6mo",
        examples=["6mo"],
    ),
) -> str:
    """지난 기간 동안 기술 섹터 내 애널리스트의 업그레이드/다운그레이드 정보를 요약하여 반환합니다."""

    # 여기에 기술 섹터 관련 애널리스트 평가 정보 조회 및 요약 코드를 추가합니다.

    return f"Tech sector analyst upgrade/downgrade summary over {period}"
