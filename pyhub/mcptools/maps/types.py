from pyhub.mcptools.core.types import PyHubIntegerChoices, PyHubTextChoices


class NaverMapRouteOptions(PyHubTextChoices):
    FASTEST = "trafast", "실시간 빠른 길"
    COMFORTABLE = "tracomfort", "실시간 편한 길"
    OPTIMAL = "traoptimal", "실시간 최적"
    AVOID_TOLL = "traavoidtoll", "무료 우선"
    AVOID_EXPRESSWAY = "traavoidcaronly", "자동차 전용 도로 회피 우선"


# 차량 타입 (톨게이트 요금 계산용)
class NaverMapCarTypes(PyHubIntegerChoices):
    GENERIC_CAR = 1, "1종 소형차"
    MEDIUM_CAR = 2, "2종 2축 차량"
    LARGE_CAR = 3, "3종 대형차"
    LARGE_TRUCK_3AXIS = 4, "4종 3축 대형 화물차"
    SPECIAL_TRUCK = 5, "5종 4축 이상 특수 화물차"
    COMPACT_CAR = 6, "1종 경형 자동차"


# 연료 타입 (유류비 계산용)
class NaverMapFuelTypes(PyHubTextChoices):
    GASOLINE = "gasoline", "휘발유"
    HIGH_GRADE_GASOLINE = "highgradegasoline", "고급 휘발유"
    DIESEL = "diesel", "경유"
    LPG = "lpg", "LPG"


class NaverMapResponseLanguages(PyHubTextChoices):
    KOREAN = "ko", "한국어"
    ENGLISH = "en", "영어"
    JAPANESE = "ja", "일본어"
    CHINESE = "zh", "중국어 간체"


class NaverMapGeocodingResponseLanguages(PyHubTextChoices):
    KOREAN = "kor", "한국어"
    ENGLISH = "eng", "영어"
