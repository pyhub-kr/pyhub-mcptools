# Python REPL 도구

안전한 Python REPL(Read-Eval-Print Loop) 환경을 제공하여 Claude Desktop에서 데이터 분석과 시각화를 수행할 수 있습니다.

## 주요 기능

- **안전한 실행 환경**: 격리된 서브프로세스에서 제한된 권한으로 실행
- **데이터 분석**: pandas, numpy를 활용한 완전한 데이터 분석 지원
- **시각화**: matplotlib, seaborn을 통한 차트 생성 (선택적 설치)
- **보안 우선**: 파일 시스템 접근 불가, 네트워크 접근 불가, 위험한 작업 차단

## 지원 라이브러리

- `pandas` (pd) - 데이터 조작 및 분석
- `numpy` (np) - 수치 연산
- `matplotlib.pyplot` (plt) - 플로팅 및 시각화
- `seaborn` (sns) - 통계 데이터 시각화
- `math` - 수학 함수
- `statistics` - 통계 함수
- `datetime` - 날짜 및 시간 작업
- `json` - JSON 데이터 처리
- `csv` - CSV 파일 작업
- `re` - 정규표현식
- `collections` - Counter, defaultdict
- `io` - StringIO를 통한 데이터 로딩

## 보안 기능

- **제한된 임포트**: 화이트리스트에 있는 모듈만 임포트 가능
- **시스템 접근 차단**: os, sys, subprocess 등 접근 불가
- **파일 접근 차단**: 파일 읽기/쓰기 불가
- **네트워크 접근 차단**: 네트워크 요청 불가
- **실행 시간 제한**: 설정 가능한 타임아웃 (기본 30초, 최대 300초)
- **프로세스 격리**: 별도 서브프로세스에서 실행

## 사용 예제

### 기본 Python 실행

```python
# 간단한 계산
코드: print(2 + 2)
결과: 4

# 데이터 분석
코드:
import pandas as pd

data = {
    'product': ['A', 'B', 'C'],
    'sales': [100, 150, 80],
    'profit': [20, 35, 15]
}

df = pd.DataFrame(data)
print("판매 요약:")
print(df.describe())
print(f"\\n총 이익: ${df['profit'].sum()}")
```

### 시각화 생성

matplotlib가 설치된 경우, 차트를 생성할 수 있습니다:

```python
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y, 'b-', label='sin(x)')
plt.xlabel('x')
plt.ylabel('y')
plt.title('사인 곡선')
plt.grid(True)
plt.legend()
```

결과는 base64로 인코딩된 PNG 이미지로 반환됩니다.

### python_analyze_data 도구 사용

일반적인 데이터 분석 작업을 위한 편리한 도구:

```python
# 기본 통계
python_analyze_data(
    data="name,age,score\\nAlice,25,85\\nBob,30,92",
    analysis_type="describe"
)

# 사용자 정의 분석
python_analyze_data(
    data=csv_data,
    analysis_type="custom",
    custom_code="print(df.groupby('category').mean())"
)
```

## 설치

Python 도구는 pyhub-mcptools에 포함되어 있습니다. 시각화 기능을 사용하려면:

```bash
pip install "pyhub-mcptools[python]"
```

이 명령은 다음 선택적 의존성을 설치합니다:
- pandas
- numpy
- matplotlib
- seaborn

## 제한사항

- 파일이나 네트워크 리소스에 접근 불가
- 화이트리스트에 있는 라이브러리만 사용 가능
- 최대 실행 시간 300초
- 서브프로세스 제약에 따른 메모리 제한
- 대화형 입력(input()) 사용 불가
- 스레딩이나 멀티프로세싱 사용 불가
- 코드 실행 함수(eval, exec) 사용 불가

## 도구 목록

### python_repl

안전한 샌드박스 환경에서 Python 코드를 실행합니다.

**매개변수:**
- `code`: 실행할 Python 코드
- `timeout_seconds`: 최대 실행 시간 (1-300초, 기본값: 30)

**반환값:**
```json
{
    "output": "코드의 stdout 출력",
    "error": "오류 메시지 (있는 경우)",
    "image": "base64 인코딩된 PNG (플롯이 생성된 경우)"
}
```

### python_analyze_data

pandas를 사용하여 데이터를 분석하고 시각화를 생성합니다.

**매개변수:**
- `data`: CSV 또는 JSON 형식의 데이터
- `analysis_type`: 수행할 분석 유형 ("describe", "correlation", "plot", "custom")
- `custom_code`: 사용자 정의 분석 코드 (analysis_type="custom"일 때)
- `plot_type`: 생성할 플롯 유형 (analysis_type="plot"일 때)
- `columns`: 분석할 컬럼명 (쉼표로 구분)