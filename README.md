# FX Trader

실시간 환율 정보를 기반으로 한 외환 거래 관리 시스템입니다.

## 주요 기능

### 1. 실시간 환율 모니터링
- USD/KRW, JPY/KRW 실시간 환율 정보 표시
- 10초 간격으로 자동 업데이트
- 보유 외화의 현재가치 및 손익 실시간 계산

### 2. 거래 관리
- 매수/매도 거래 기록
- 거래별 메모 기능
- 거래 수정 및 삭제
- 매수 거래별 매도 내역 필터링

### 3. 자동화된 매매 계획
- 매수 예정 환율 자동 계산 (현재가 또는 마지막 매수가 기준)
- 매도 예정 환율 3단계 설정
- 손절 환율 설정
- 기본 매수 금액 설정

## 기술 스택

- Backend: Python Flask
- Frontend: Bootstrap 5
- Database: JSON 파일 기반
- 환율 정보: investing.com 실시간 데이터

## 설치 방법

1. 저장소 클론
```bash
git clone https://github.com/yourusername/fxtrader.git
cd fxtrader
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 서버 실행
```bash
python -m flask run
```

## 설정 파일

`settings.json` 파일에서 다음 설정을 관리합니다:
- 매도 예정 환율 상승폭 (1차, 2차, 3차)
- 손절 환율 하락폭
- 기본 매수 금액
- 매수 예정 하락폭

## 라이선스

MIT License