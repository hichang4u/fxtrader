import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
import cloudscraper
import time

@dataclass
class RateData:
    """환율 데이터를 저장하는 클래스"""
    currency: str           # 통화 (USD/JPY)
    current_rate: float    # 현재 환율
    change_amount: float   # 등락금액
    change_percent: float  # 등락률
    timestamp: str        # 실시간 데이터 시간

class RateMonitor:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        self.initialized_currencies = set()
        self.buy_drop_thresholds = {
            'USD': 5,  # 기본값 설정
            'JPY': 3   # 기본값 설정
        }
        
    def get_current_rate(self, currency, is_update=False) -> Optional[RateData]:
        """investing.com에서 환율 정보를 스크래핑합니다."""
        try:
            if currency == 'USD':
                url = 'https://kr.investing.com/currencies/usd-krw'
            else:  # JPY
                url = 'https://kr.investing.com/currencies/jpy-krw'
            
            # 첫 로드시에만 전체 페이지를 가져옴
            if not currency in self.initialized_currencies:
                response = self.scraper.get(url, headers=self.headers)
                if response.status_code != 200:
                    print(f"{currency} 초기 페이지 로드 실패: {response.status_code}")
                    return None
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 현재가
                current_element = soup.find('div', {'data-test': 'instrument-price-last'})
                if not current_element:
                    print(f"{currency} 환율 스크래핑 실패")
                    return None
                
                current_rate = float(current_element.text.replace(',', ''))
                if currency == 'JPY':  # JPY의 경우 1엔당 가격을 100엔당 가격으로 변환
                    current_rate = current_rate * 100
                
                # 등락 정보
                change_element = soup.find('span', {'data-test': 'instrument-price-change'})
                percent_element = soup.find('span', {'data-test': 'instrument-price-change-percent'})
                
                if not change_element or not percent_element:
                    print(f"{currency} 등락 정보 스크래핑 실패")
                    return None
                
                # +/- 기호와 숫자 분리, HTML 주석 제거
                change_text = change_element.text.replace('<!-- -->', '').replace(',', '')
                change_amount = float(change_text)
                if currency == 'JPY':  # JPY의 경우 1엔당 변화량을 100엔당 변화량으로 변환
                    change_amount = change_amount * 100
                
                # 퍼센트 정보에서 괄호, %, HTML 주석 제거
                percent_text = percent_element.text
                for char in ['(', ')', '%', '<!-- -->', ',']:
                    percent_text = percent_text.replace(char, '')
                change_percent = float(percent_text)
                
                # 시간 정보
                time_element = soup.find('time', {'data-test': 'trading-time-label'})
                current_time = time_element.text if time_element else datetime.now().strftime("%H:%M:%S")
                
                print(f"{currency} {current_rate:.2f}원 ({change_amount:+.2f}원, {change_percent:+.2f}%) {current_time} (초기)")
                
                self.initialized_currencies.add(currency)
                
                return RateData(
                    currency=currency,
                    current_rate=current_rate,
                    change_amount=change_amount,
                    change_percent=change_percent,
                    timestamp=current_time
                )
            
            # 이후 업데이트는 현재 표시된 데이터만 가져옴
            response = self.scraper.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"{currency} 데이터 요청 실패: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 현재가만 업데이트
            current_element = soup.find('div', {'data-test': 'instrument-price-last'})
            if not current_element:
                print(f"{currency} 실시간 환율 스크래핑 실패")
                return None
            
            current_rate = float(current_element.text.replace(',', ''))
            if currency == 'JPY':
                current_rate = current_rate * 100
                
            # 등락 정보
            change_element = soup.find('span', {'data-test': 'instrument-price-change'})
            percent_element = soup.find('span', {'data-test': 'instrument-price-change-percent'})
            
            if not change_element or not percent_element:
                print(f"{currency} 실시간 등락 정보 스크래핑 실패")
                return None
            
            change_text = change_element.text.replace('<!-- -->', '').replace(',', '')
            change_amount = float(change_text)
            if currency == 'JPY':
                change_amount = change_amount * 100
            
            percent_text = percent_element.text
            for char in ['(', ')', '%', '<!-- -->', ',']:
                percent_text = percent_text.replace(char, '')
            change_percent = float(percent_text)
            
            time_element = soup.find('time', {'data-test': 'trading-time-label'})
            current_time = time_element.text if time_element else datetime.now().strftime("%H:%M:%S")
            
            print(f"{currency} {current_rate:.2f}원 ({change_amount:+.2f}원, {change_percent:+.2f}%) {current_time} (실시간)")
            
            return RateData(
                currency=currency,
                current_rate=current_rate,
                change_amount=change_amount,
                change_percent=change_percent,
                timestamp=current_time
            )
            
        except Exception as e:
            print(f"{currency} 환율 스크래핑 중 오류: {str(e)}")
            return None 