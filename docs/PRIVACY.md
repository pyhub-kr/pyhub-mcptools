# 개인정보처리방침

**최종 업데이트**: 2025년 6월

## 1. 개요

pyhub-mcptools는 사용자의 컴퓨터에서 로컬로 실행되는 MCP(Model Context Protocol) 도구 모음입니다. 본 도구는 Google Sheets, Microsoft Excel 등의 서비스와 연동하여 데이터를 조회하고 조작할 수 있는 기능을 제공합니다.

**중요**: 본 도구는 사용자의 개인정보를 수집하거나 외부 서버로 전송하지 않습니다.

## 2. 서비스 제공자 정보

- **서비스명**: 파이썬사랑방 MCP 도구
- **개발 및 운영**: 파이썬사랑방
- **연락처**: me@pyhub.kr
- **소재지**: 대한민국

## 3. 처리하는 개인정보

### 3.1 수집하지 않는 정보
pyhub-mcptools는 다음과 같은 개인정보를 **수집하지 않습니다**:
- 사용자 식별 정보 (이름, 이메일, 전화번호 등)
- 사용 통계 및 로그
- 사용자 행동 분석 데이터
- 크래시 리포트 또는 오류 정보
- Google Sheets, Excel 등에서 조회한 실제 데이터

### 3.2 로컬에만 저장되는 정보
다음 정보는 **사용자의 컴퓨터에만 저장**되며, 외부로 전송되지 않습니다:

#### Google Sheets 연동 시
- OAuth 2.0 액세스 토큰
- OAuth 2.0 갱신 토큰
- 저장 위치: `~/.pyhub-mcptools/credentials/google_sheets_token.json`
- 보관 기간: 사용자가 직접 삭제할 때까지 (무기한)

#### Microsoft Excel 연동 시
- Excel 애플리케이션 연결 정보 (로컬 COM 객체)
- 임시 파일 정보 (세션 종료 시 자동 삭제)

## 4. 개인정보의 처리 목적

저장되는 인증 정보는 다음 목적으로만 사용됩니다:
- Google Sheets API 인증 및 데이터 조회/수정
- Microsoft Excel 파일 접근 및 조작
- 사용자 재인증 빈도 최소화를 통한 편의성 제공

## 5. 개인정보의 보관 및 이용 기간

- **OAuth 토큰**: 사용자가 직접 삭제할 때까지 무기한 보관
- **임시 파일**: 세션 종료 시 자동 삭제
- **사용자가 직접 삭제하는 방법**:
  ```bash
  rm -rf ~/.pyhub-mcptools/credentials/
  ```

## 6. 개인정보의 제3자 제공

pyhub-mcptools는 **어떠한 개인정보도 제3자에게 제공하지 않습니다**.

## 7. 개인정보 보호 조치

### 7.1 기술적 보호조치
- OAuth 토큰 파일 권한: 소유자만 읽기/쓰기 가능 (0o600)
- HTTPS를 통한 암호화된 API 통신
- 로컬 저장소 외부 접근 차단

### 7.2 관리적 보호조치
- 개인정보 수집 최소화 원칙 준수
- 로컬 실행으로 데이터 외부 유출 원천 차단

## 8. 사용자의 권리

### 8.1 정보 삭제권
사용자는 언제든지 저장된 인증 정보를 삭제할 수 있습니다:
```bash
# Google Sheets 인증 정보 삭제
rm ~/.pyhub-mcptools/credentials/google_sheets_token.json

# 모든 인증 정보 삭제
rm -rf ~/.pyhub-mcptools/credentials/
```

### 8.2 서비스 연동 해제
- Google: [Google 계정 보안 설정](https://myaccount.google.com/permissions)에서 앱 권한 철회
- Microsoft: 로컬 Excel 애플리케이션 종료

## 9. 제3자 서비스 연동

### 9.1 Google Sheets API
- **목적**: 스프레드시트 데이터 조회 및 수정
- **수집 범위**: OAuth 2.0 토큰만 로컬 저장
- **Google 개인정보처리방침**: https://policies.google.com/privacy

### 9.2 Microsoft Excel
- **목적**: Excel 파일 데이터 조회 및 수정
- **연동 방식**: 로컬 COM 객체 (네트워크 통신 없음)

## 10. 개인정보처리방침의 변경

본 개인정보처리방침이 변경되는 경우:
- GitHub 저장소를 통한 변경 내역 공지
- 중요한 변경 시 사용자 공지
- 변경된 방침은 공지 후 즉시 적용

## 11. 개인정보 보호책임자

- **담당자**: pyhub-kr (파이썬사랑방)
- **연락처**: me@pyhub.kr
- **문의 방법**: 이메일 또는 [GitHub Issues](https://github.com/pyhub-kr/pyhub-mcptools/issues)

## 12. 기타

본 개인정보처리방침은 대한민국의 개인정보보호법을 준수하여 작성되었습니다.

---

**이 문서는 pyhub-mcptools의 로컬 실행 특성을 반영하여 작성되었으며, 실제 개인정보 수집이나 외부 전송이 없음을 명확히 고지합니다.**
