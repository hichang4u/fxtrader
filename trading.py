from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
import json
from rate_monitor import RateMonitor
import threading

@dataclass
class CurrencySettings:
    """통화별 거래 설정"""
    currency: str
    rate_increments: List[int]  # 매도 예정 환율 상승폭 [1차, 2차, 3차]
    stop_loss_gap: int         # 손절 환율 하락폭
    default_amount: int        # 기본 매수 금액
    buy_drop_threshold: int    # 매수 예정 하락폭
    planned_buy_amount: int    # 매수 예정 금액
    planned_buy_rate: int      # 매수 예정 환율

    def __init__(self, currency: str = '', rate_increments=None, stop_loss_gap=20, 
                 default_amount=100000, buy_drop_threshold=5, planned_buy_amount=100000,
                 planned_buy_rate=0):
        self.currency = currency
        self.rate_increments = rate_increments or [10, 20, 30]
        self.stop_loss_gap = stop_loss_gap
        self.default_amount = default_amount
        self.buy_drop_threshold = buy_drop_threshold
        self.planned_buy_amount = planned_buy_amount
        self.planned_buy_rate = int(planned_buy_rate)  # float를 int로 변환

    def to_dict(self):
        return {
            'currency': self.currency,
            'rate_increments': self.rate_increments,
            'stop_loss_gap': self.stop_loss_gap,
            'default_amount': self.default_amount,
            'buy_drop_threshold': self.buy_drop_threshold,
            'planned_buy_amount': self.planned_buy_amount,
            'planned_buy_rate': self.planned_buy_rate
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            currency=data['currency'],
            rate_increments=data.get('rate_increments', [10, 20, 30]),
            stop_loss_gap=data.get('stop_loss_gap', 20),
            default_amount=data.get('default_amount', 100000),
            buy_drop_threshold=data.get('buy_drop_threshold', 5 if data['currency'] == 'USD' else 3),
            planned_buy_amount=data.get('planned_buy_amount', 100000),
            planned_buy_rate=data.get('planned_buy_rate', 0)
        )

@dataclass
class Trade:
    id: str
    date: str
    type: str
    currency: str        # 'USD' 또는 'JPY'
    rate: float
    krw_amount: float
    foreign_amount: float  # usd_amount를 foreign_amount로 변경
    profit: float
    note: str
    related_id: str

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'type': self.type,
            'currency': self.currency,
            'rate': self.rate,
            'krw_amount': self.krw_amount,
            'foreign_amount': self.foreign_amount,
            'profit': self.profit,
            'note': self.note,
            'related_id': self.related_id
        }

class TradingSystem:
    def __init__(self, file_path: str = 'trades.json', settings_path: str = 'settings.json'):
        self.file_path = file_path
        self.settings_path = settings_path
        self.trades: List[Trade] = []
        self.settings: Dict[str, CurrencySettings] = {}
        self.rate_monitor = RateMonitor()
        self.load_trades()
        self.load_settings()
        
        # 환율 모니터링 스레드 시작
        self.monitor_thread = threading.Thread(target=self._start_rate_monitoring, daemon=True)
        self.monitor_thread.start()
    
    def _start_rate_monitoring(self):
        """백그라운드에서 환율 모니터링을 시작합니다."""
        self.rate_monitor.threshold = 0.1  # 환율 변동 감지 기준 설정
        import schedule
        import time
        
        schedule.every(1).minutes.do(self._check_rates)
        
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def _check_rates(self):
        """환율을 체크하고 필요한 작업을 수행합니다."""
        for currency in ['USD', 'JPY']:
            current_rate = self.rate_monitor.get_current_rate(currency)
            if current_rate is not None:
                # 여기에 환율 변동에 따른 추가 로직 구현 가능
                # 예: 손절가 도달 시 알림, 목표가 도달 시 알림 등
                pass

    def load_trades(self):
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                self.trades = []
                for trade in data:
                    # 이전 데이터 구조를 새 구조로 변환
                    if 'usd_amount' in trade:
                        trade['foreign_amount'] = trade.pop('usd_amount')
                    if 'currency' not in trade:
                        trade['currency'] = 'USD'  # 기존 데이터는 모두 USD로 처리
                    self.trades.append(Trade(**trade))
        except FileNotFoundError:
            self.trades = []

    def save_trades(self):
        with open(self.file_path, 'w') as f:
            json.dump([trade.to_dict() for trade in self.trades], f, indent=2)

    def load_settings(self):
        """설정 파일 로드"""
        try:
            with open(self.settings_path, 'r') as f:
                data = json.load(f)
                self.settings = {
                    currency: CurrencySettings.from_dict(settings)
                    for currency, settings in data.items()
                }
        except FileNotFoundError:
            # 기본 설정 생성
            self.settings = {
                'USD': CurrencySettings(
                    currency='USD',
                    rate_increments=[10, 20, 30],  # USD는 10원씩 상승
                    stop_loss_gap=20,              # USD는 20원 하락
                    default_amount=100000,         # 10만원
                    buy_drop_threshold=5           # 5원
                ),
                'JPY': CurrencySettings(
                    currency='JPY',
                    rate_increments=[6, 12, 18],   # JPY는 6원씩 상승
                    stop_loss_gap=6,               # JPY는 6원 하락
                    default_amount=100000,         # 10만원
                    buy_drop_threshold=3           # 3원
                )
            }
            self.save_settings()

    def save_settings(self):
        """설정 파일 저장"""
        with open(self.settings_path, 'w') as f:
            json.dump({
                currency: settings.to_dict()
                for currency, settings in self.settings.items()
            }, f, indent=2)

    def update_currency_settings(self, currency: str, rate_increments: List[int], stop_loss_gap: int, 
                                default_amount: int, buy_drop_threshold: int, planned_buy_rate: float):
        """통화별 설정을 업데이트합니다."""
        self.settings[currency] = CurrencySettings(
            currency=currency,
            rate_increments=rate_increments,
            stop_loss_gap=stop_loss_gap,
            default_amount=default_amount,
            buy_drop_threshold=buy_drop_threshold,
            planned_buy_rate=int(planned_buy_rate)
        )
        # 매수 예정 하락폭 설정을 RateMonitor에도 전달
        self.rate_monitor.buy_drop_thresholds[currency] = buy_drop_threshold
        self.save_settings()

    def get_currency_settings(self, currency: str) -> CurrencySettings:
        """통화별 설정 조회"""
        return self.settings.get(currency)

    def create_buy_order(self, krw_amount: float, rate: float, currency: str, date: str = None, note: str = "") -> Trade:
        # 매수 ID 생성
        buy_id = f"매수{len([t for t in self.trades if t.type == '매수']) + 1}"
        
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 통화별 설정 가져오기
        settings = self.get_currency_settings(currency)
        if not settings:
            raise ValueError(f"지원하지 않는 통화입니다: {currency}")
        
        # 매수 주문 생성
        buy_trade = Trade(
            id=buy_id,
            date=date,
            type="매수",
            currency=currency,
            rate=rate,
            krw_amount=round(krw_amount, 2),
            foreign_amount=round(krw_amount / rate, 4 if currency == "JPY" else 2),
            profit=0,
            note=note,
            related_id=""
        )
        
        # 매도예정 주문 생성 (30%, 30%, 40% 분할)
        sell_ratios = [0.3, 0.3, 0.4]
        sell_planned_trades = []
        
        for i, (ratio, rate_inc) in enumerate(zip(sell_ratios, settings.rate_increments), 1):
            sell_amount = round(krw_amount * ratio, 2)
            sell_rate = rate + rate_inc
            foreign_amount = round(sell_amount / sell_rate, 4 if currency == "JPY" else 2)
            buy_amount = round(foreign_amount * rate, 2)
            expected_profit = round(sell_amount - buy_amount, 2)
            
            sell_planned = Trade(
                id=f"매도예정{buy_id[2:]}-{i}",
                date=date,
                type="매도예정",
                currency=currency,
                rate=sell_rate,
                krw_amount=sell_amount,
                foreign_amount=foreign_amount,
                profit=expected_profit,
                note=f"자동생성 (분할 {i}/3, +{rate_inc}{'원'})",
                related_id=buy_id
            )
            sell_planned_trades.append(sell_planned)
        
        # 손절예정 주문 생성
        stop_loss_rate = rate - settings.stop_loss_gap
        stop_loss_amount = krw_amount
        foreign_amount = round(stop_loss_amount / stop_loss_rate, 4 if currency == "JPY" else 2)
        expected_loss = round((stop_loss_amount * (stop_loss_rate / rate)) - stop_loss_amount, 2)
        
        stop_loss = Trade(
            id=f"손절예정{buy_id[2:]}",
            date=date,
            type="손절예정",
            currency=currency,
            rate=stop_loss_rate,
            krw_amount=stop_loss_amount,
            foreign_amount=foreign_amount,
            profit=expected_loss,
            note=f"자동생성 (-{settings.stop_loss_gap}{'엔' if currency == 'JPY' else '원'})",
            related_id=buy_id
        )
        
        # 다음 매수예정 주문 생성
        next_buy_rate = rate - settings.buy_drop_threshold
        next_buy = Trade(
            id=f"매수예정{buy_id[2:]}",
            date=date,
            type="매수예정",
            currency=currency,
            rate=next_buy_rate,
            krw_amount=settings.default_amount,
            foreign_amount=round(settings.default_amount / next_buy_rate, 4 if currency == "JPY" else 2),
            profit=0,
            note=f"자동생성 (-{settings.buy_drop_threshold}{'엔' if currency == 'JPY' else '원'})",
            related_id=buy_id
        )
        
        self.trades.extend([buy_trade] + sell_planned_trades + [stop_loss, next_buy])
        self.save_trades()
        return buy_trade

    def create_sell_order(self, buy_id: str, rate: float, ratio: float, date: str = None, note: str = "") -> Trade:
        # 매수 주문 찾기
        buy_trade = next((t for t in self.trades if t.id == buy_id), None)
        if not buy_trade:
            raise ValueError(f"매수 주문을 찾을 수 없습니다: {buy_id}")
        
        # 날짜가 없으면 현재 날짜 사용
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 매도 금액 계산
        sell_krw = round(buy_trade.krw_amount * ratio, 2)
        sell_usd = round(sell_krw / rate, 2)
        profit = round(sell_krw - (buy_trade.krw_amount * ratio), 2)
        
        sell_trade = Trade(
            id=f"매도{len([t for t in self.trades if t.type == '매도']) + 1}",
            date=date,
            type="매도",
            rate=rate,
            krw_amount=sell_krw,
            foreign_amount=sell_usd,
            profit=profit,
            note=note,
            related_id=buy_id
        )
        
        self.trades.append(sell_trade)
        self.save_trades()
        return sell_trade

    def create_stop_loss(self, buy_id: str, rate: float, note: str = "") -> Trade:
        buy_trade = next((t for t in self.trades if t.id == buy_id), None)
        if not buy_trade:
            raise ValueError(f"매수 주문을 찾을 수 없습니다: {buy_id}")
        
        loss = round(buy_trade.krw_amount - (buy_trade.foreign_amount * rate), 2)
        
        stop_loss_trade = Trade(
            id=f"손절{len([t for t in self.trades if t.type == '손절']) + 1}",
            date=datetime.now().strftime("%Y-%m-%d"),
            type="손절",
            rate=rate,
            krw_amount=buy_trade.krw_amount,
            foreign_amount=buy_trade.foreign_amount,
            profit=loss,
            note=note,
            related_id=buy_id
        )
        
        self.trades.append(stop_loss_trade)
        self.save_trades()
        return stop_loss_trade 

    def get_all_trades(self) -> List[Trade]:
        return self.trades

    def get_related_trades(self, buy_id: str) -> List[Trade]:
        return [t for t in self.trades if t.related_id == buy_id or t.id == buy_id]

    def get_planned_trades(self) -> List[Trade]:
        return [t for t in self.trades if t.type in ['매도예정', '손절예정']]

    def calculate_total_profit(self) -> float:
        return sum(t.profit for t in self.trades if t.type in ['매도', '손절']) 

    def has_related_sells(self, buy_id: str) -> bool:
        """매수 거래와 연관된 매도 거래가 있는지 확인합니다."""
        return any(t for t in self.trades if t.type == '매도' and t.related_id == buy_id)

    def delete_trade(self, trade_id: str) -> None:
        """거래를 삭제합니다. 매수 거래인 경우 관련된 매도예정/손절예정 거래도 함께 삭제됩니다."""
        # 거래 찾기
        trade = next((t for t in self.trades if t.id == trade_id), None)
        if not trade:
            raise ValueError(f"거래를 찾을 수 없습니다: {trade_id}")
        
        # 매수 거래인 경우 연관된 매도 거래가 있는지 확인
        if trade.type == "매수" and self.has_related_sells(trade_id):
            raise ValueError("이 매수 거래와 연관된 매도 거래가 있어 삭제할 수 없습니다.")
        
        # 매수 거래인 경우 관련된 모든 거래 삭제
        if trade.type == "매수":
            self.trades = [t for t in self.trades if t.related_id != trade_id and t.id != trade_id]
        else:
            # 매수가 아닌 경우 해당 거래만 삭제
            self.trades = [t for t in self.trades if t.id != trade_id]
        
        self.save_trades() 

    def update_trade(self, trade_id: str, date: str, rate: float, krw_amount: float, note: str) -> Trade:
        # 거래 찾기
        trade = next((t for t in self.trades if t.id == trade_id), None)
        if not trade:
            raise ValueError(f"거래를 찾을 수 없습니다: {trade_id}")
        
        # 매수 거래인 경우
        if trade.type == "매수":
            # 기존 예정 거래들 삭제
            self.trades = [t for t in self.trades if t.related_id != trade_id]
            
            # 거래 업데이트
            trade.date = date
            trade.rate = rate
            trade.krw_amount = round(krw_amount, 2)
            trade.foreign_amount = round(krw_amount / rate, 4 if trade.currency == "JPY" else 2)
            trade.note = note
            
            # 통화별 설정 가져오기
            settings = self.get_currency_settings(trade.currency)
            if not settings:
                raise ValueError(f"지원하지 않는 통화입니다: {trade.currency}")
            
            # 매도예정 주문 생성 (30%, 30%, 40% 분할)
            sell_ratios = [0.3, 0.3, 0.4]
            sell_planned_trades = []
            
            for i, (ratio, rate_inc) in enumerate(zip(sell_ratios, settings.rate_increments), 1):
                sell_amount = round(krw_amount * ratio, 2)
                sell_rate = rate + rate_inc
                foreign_amount = round(sell_amount / sell_rate, 4 if trade.currency == "JPY" else 2)
                buy_amount = round(foreign_amount * rate, 2)
                expected_profit = round(sell_amount - buy_amount, 2)
                
                sell_planned = Trade(
                    id=f"매도예정{trade_id[2:]}-{i}",
                    date=date,
                    type="매도예정",
                    currency=trade.currency,
                    rate=sell_rate,
                    krw_amount=sell_amount,
                    foreign_amount=foreign_amount,
                    profit=expected_profit,
                    note=f"자동생성 (분할 {i}/3, +{rate_inc}{'엔' if trade.currency == 'JPY' else '원'})",
                    related_id=trade_id
                )
                sell_planned_trades.append(sell_planned)
            
            # 손절예정 주문 생성
            stop_loss_rate = rate - settings.stop_loss_gap
            stop_loss_amount = krw_amount
            foreign_amount = round(stop_loss_amount / stop_loss_rate, 4 if trade.currency == "JPY" else 2)
            expected_loss = round((stop_loss_amount * (stop_loss_rate / rate)) - stop_loss_amount, 2)
            
            stop_loss = Trade(
                id=f"손절예정{trade_id[2:]}",
                date=date,
                type="손절예정",
                currency=trade.currency,
                rate=stop_loss_rate,
                krw_amount=stop_loss_amount,
                foreign_amount=foreign_amount,
                profit=expected_loss,
                note=f"자동생성 (-{settings.stop_loss_gap}{'엔' if trade.currency == 'JPY' else '원'})",
                related_id=trade_id
            )
            
            # 모든 거래 추가
            self.trades.extend(sell_planned_trades + [stop_loss])
        
        # 매도 거래인 경우
        elif trade.type == "매도":
            # 거래 업데이트
            trade.date = date
            trade.rate = rate
            trade.krw_amount = round(krw_amount, 2)
            trade.foreign_amount = round(krw_amount / rate, 4 if trade.currency == "JPY" else 2)
            trade.note = note
            
            # 수익 재계산
            buy_trade = next((t for t in self.trades if t.id == trade.related_id), None)
            if buy_trade:
                ratio = krw_amount / buy_trade.krw_amount
                trade.profit = round(krw_amount - (buy_trade.krw_amount * ratio), 2)
        
        self.save_trades()
        return trade 

    def calculate_currency_profit(self, currency: str) -> float:
        """특정 통화의 실현 손익을 계산합니다."""
        return sum(t.profit for t in self.trades if t.currency == currency and t.type in ['매도', '손절']) 

    def calculate_total_buy_amount(self, currency: str) -> float:
        """특정 통화의 총 매수금액을 계산합니다."""
        return sum(t.krw_amount for t in self.trades if t.currency == currency and t.type == '매수') 

    def calculate_holding_amount(self, currency: str) -> dict:
        """특정 통화의 보유금액 정보를 계산합니다."""
        # 매수 거래 합계
        total_buy = sum(t.foreign_amount for t in self.trades 
                       if t.currency == currency and t.type == '매수')
        
        # 매도/손절 거래 합계
        total_sell = sum(t.foreign_amount for t in self.trades 
                        if t.currency == currency and t.type in ['매도', '손절'])
        
        # 보유 외화 수량
        holding_amount = total_buy - total_sell
        
        # 매수 평균 단가 계산
        buy_trades = [t for t in self.trades if t.currency == currency and t.type == '매수']
        if buy_trades:
            avg_rate = sum(t.krw_amount for t in buy_trades) / sum(t.foreign_amount for t in buy_trades)
        else:
            avg_rate = 0
        
        # 보유 원화 금액 (매수 평균단가 기준)
        holding_krw = holding_amount * avg_rate
        
        return {
            'holding_amount': holding_amount,  # 보유 외화 수량
            'avg_rate': avg_rate,             # 매수 평균단가
            'holding_krw': holding_krw        # 보유 원화 금액
        }

    def calculate_current_value(self, currency: str, current_rate: float, holding_info: dict) -> dict:
        """현재 환율 기준 보유 자산의 가치와 손익률을 계산합니다."""
        if holding_info['holding_amount'] == 0 or current_rate == 0:
            return {
                'current_value': 0,    # 현재 가치 (원화)
                'profit_amount': 0,    # 평가 손익 (원화)
                'profit_rate': 0       # 손익률 (%)
            }
        
        # 현재 가치 계산
        current_value = holding_info['holding_amount'] * current_rate
        
        # 평가 손익 계산
        profit_amount = current_value - holding_info['holding_krw']
        
        # 손익률 계산
        profit_rate = (profit_amount / holding_info['holding_krw']) * 100 if holding_info['holding_krw'] != 0 else 0
        
        return {
            'current_value': current_value,
            'profit_amount': profit_amount,
            'profit_rate': profit_rate
        } 