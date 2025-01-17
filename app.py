from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from trading import TradingSystem
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # 플래시 메시지를 위한 시크릿 키
trading_system = TradingSystem()

@app.route('/')
def index():
    """메인 페이지"""
    # 실제 거래만 필터링 (매수, 매도만 표시)
    actual_trades = [t for t in trading_system.get_all_trades() if t.type in ['매수', '매도']]
    planned_trades = trading_system.get_planned_trades()
    total_profit = trading_system.calculate_total_profit()
    
    # 매도 거래가 있는 매수 거래 ID 목록
    trades_with_sells = [t.id for t in actual_trades if t.type == '매수' and trading_system.has_related_sells(t.id)]
    
    # 환율 정보 가져오기
    usd_rate = trading_system.rate_monitor.get_current_rate('USD')
    jpy_rate = trading_system.rate_monitor.get_current_rate('JPY')
    
    # 통화별 설정 가져오기
    usd_settings = trading_system.get_currency_settings('USD')
    jpy_settings = trading_system.get_currency_settings('JPY')
    
    # 통화별 보유금액 정보 계산
    usd_holding = trading_system.calculate_holding_amount('USD')
    jpy_holding = trading_system.calculate_holding_amount('JPY')
    
    # 현재가치 및 손익률 계산
    usd_current_value = trading_system.calculate_current_value('USD', 
        usd_rate.current_rate if usd_rate else 0, usd_holding)
    jpy_current_value = trading_system.calculate_current_value('JPY', 
        jpy_rate.current_rate if jpy_rate else 0, jpy_holding)
    
    # 통화별 손익 계산
    usd_profit = trading_system.calculate_currency_profit('USD')
    jpy_profit = trading_system.calculate_currency_profit('JPY')
    
    return render_template('index.html',
                         trades=actual_trades,
                         planned_trades=planned_trades,
                         total_profit=total_profit,
                         trades_with_sells=trades_with_sells,
                         selected_buy_id=None,
                         usd_rate=usd_rate,
                         jpy_rate=jpy_rate,
                         usd_settings=usd_settings,
                         jpy_settings=jpy_settings,
                         usd_holding=usd_holding,
                         jpy_holding=jpy_holding,
                         usd_current_value=usd_current_value,
                         jpy_current_value=jpy_current_value,
                         usd_profit=usd_profit,
                         jpy_profit=jpy_profit)

@app.route('/filter/<buy_id>')
def filter_trades(buy_id):
    actual_trades = [t for t in trading_system.get_all_trades() if t.type in ['매수', '매도']]
    # 선택된 매수 ID에 해당하는 예정 거래만 필터링
    planned_trades = [t for t in trading_system.get_planned_trades() if t.related_id == buy_id]
    total_profit = trading_system.calculate_total_profit()
    
    trades_with_sells = [t.id for t in actual_trades if t.type == '매수' and trading_system.has_related_sells(t.id)]
    
    # 환율 정보 가져오기
    usd_rate = trading_system.rate_monitor.get_current_rate('USD')
    jpy_rate = trading_system.rate_monitor.get_current_rate('JPY')
    
    # 통화별 설정 가져오기
    usd_settings = trading_system.get_currency_settings('USD')
    jpy_settings = trading_system.get_currency_settings('JPY')
    
    # 통화별 손익 계산
    usd_profit = trading_system.calculate_currency_profit('USD')
    jpy_profit = trading_system.calculate_currency_profit('JPY')
    
    return render_template('index.html',
                         trades=actual_trades,
                         planned_trades=planned_trades,
                         total_profit=total_profit,
                         trades_with_sells=trades_with_sells,
                         selected_buy_id=buy_id,
                         usd_rate=usd_rate,
                         jpy_rate=jpy_rate,
                         usd_settings=usd_settings,
                         jpy_settings=jpy_settings,
                         usd_profit=usd_profit,
                         jpy_profit=jpy_profit)

@app.route('/filter_sells/<buy_id>')
def filter_sells(buy_id):
    # 선택된 매수 거래와 연관된 매도 거래만 필터링
    actual_trades = [t for t in trading_system.get_all_trades() 
                    if (t.type == '매도' and t.related_id == buy_id) or t.id == buy_id]
    planned_trades = trading_system.get_planned_trades()
    total_profit = trading_system.calculate_total_profit()
    
    trades_with_sells = [t.id for t in actual_trades if t.type == '매수' and trading_system.has_related_sells(t.id)]
    
    # 환율 정보 가져오기
    usd_rate = trading_system.rate_monitor.get_current_rate('USD')
    jpy_rate = trading_system.rate_monitor.get_current_rate('JPY')
    
    # 통화별 설정 가져오기
    usd_settings = trading_system.get_currency_settings('USD')
    jpy_settings = trading_system.get_currency_settings('JPY')
    
    # 통화별 손익 계산
    usd_profit = trading_system.calculate_currency_profit('USD')
    jpy_profit = trading_system.calculate_currency_profit('JPY')
    
    return render_template('index.html',
                         trades=actual_trades,
                         planned_trades=planned_trades,
                         total_profit=total_profit,
                         trades_with_sells=trades_with_sells,
                         filtered_sells_for=buy_id,
                         usd_rate=usd_rate,
                         jpy_rate=jpy_rate,
                         usd_settings=usd_settings,
                         jpy_settings=jpy_settings,
                         usd_profit=usd_profit,
                         jpy_profit=jpy_profit)

@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if request.method == 'POST':
        try:
            krw_amount = float(request.form['krw_amount'])
            rate = float(request.form['rate'])
            date = request.form['date']
            note = request.form['note']
            currency = request.form['currency']
            
            trade = trading_system.create_buy_order(
                krw_amount=krw_amount,
                rate=rate,
                currency=currency,
                date=date,
                note=note
            )
            flash('매수 주문이 생성되었습니다.', 'success')
            return redirect(url_for('index'))
        except ValueError as e:
            flash(f'오류: {str(e)}', 'error')
    
    # 오늘 날짜를 기본값으로 설정
    today = datetime.now().strftime("%Y-%m-%d")
    # 기본 매수금액 설정
    default_amount = 100000
    return render_template('buy.html', today=today, default_amount=default_amount)

@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if request.method == 'POST':
        try:
            buy_id = request.form['buy_id']
            rate = float(request.form['rate'])
            ratio = float(request.form['ratio'])
            date = request.form['date']
            note = request.form['note']
            
            trade = trading_system.create_sell_order(
                buy_id=buy_id,
                rate=rate,
                ratio=ratio,
                date=date,
                note=note
            )
            flash('매도 주문이 생성되었습니다.', 'success')
            return redirect(url_for('index'))
        except ValueError as e:
            flash(f'오류: {str(e)}', 'error')
    
    buy_trades = [t for t in trading_system.get_all_trades() if t.type == '매수']
    today = datetime.now().strftime("%Y-%m-%d")  # 오늘 날짜를 기본값으로 설정
    return render_template('sell.html', buy_trades=buy_trades, today=today)

@app.route('/edit/<trade_id>', methods=['GET', 'POST'])
def edit_trade(trade_id):
    trade = next((t for t in trading_system.get_all_trades() if t.id == trade_id), None)
    if not trade or trade.type not in ['매수', '매도']:
        flash('수정할 수 없는 거래입니다.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            date = request.form['date']
            rate = float(request.form['rate'])
            krw_amount = float(request.form['krw_amount'])
            note = request.form['note']
            
            trading_system.update_trade(
                trade_id=trade_id,
                date=date,
                rate=rate,
                krw_amount=krw_amount,
                note=note
            )
            flash('거래가 수정되었습니다.', 'success')
            return redirect(url_for('index'))
        except ValueError as e:
            flash(f'오류: {str(e)}', 'error')
    
    return render_template('edit_trade.html', trade=trade)

@app.route('/delete/<trade_id>', methods=['POST'])
def delete_trade(trade_id):
    try:
        trading_system.delete_trade(trade_id)
        flash('거래가 삭제되었습니다.', 'success')
    except ValueError as e:
        flash(f'오류: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/settings')
def settings():
    """설정 페이지"""
    # 실제 거래 가져오기
    trades = [t for t in trading_system.get_all_trades() if t.type in ['매수', '매도']]
    
    # 환율 정보 가져오기
    usd_rate = trading_system.rate_monitor.get_current_rate('USD')
    jpy_rate = trading_system.rate_monitor.get_current_rate('JPY')
    
    # 통화별 설정 가져오기
    usd_settings = trading_system.get_currency_settings('USD')
    jpy_settings = trading_system.get_currency_settings('JPY')
    
    return render_template('settings.html',
                         trades=trades,
                         usd_rate=usd_rate,
                         jpy_rate=jpy_rate,
                         usd_settings=usd_settings,
                         jpy_settings=jpy_settings)

@app.route('/api/rate_cards')
def get_rate_cards():
    """환율 정보 카드 HTML을 반환"""
    is_update = request.args.get('update', 'false').lower() == 'true'
    
    usd_rate = trading_system.rate_monitor.get_current_rate('USD', is_update)
    jpy_rate = trading_system.rate_monitor.get_current_rate('JPY', is_update)
    
    # 통화별 설정 가져오기
    usd_settings = trading_system.get_currency_settings('USD')
    jpy_settings = trading_system.get_currency_settings('JPY')
    
    # 통화별 보유금액 정보 계산
    usd_holding = trading_system.calculate_holding_amount('USD')
    jpy_holding = trading_system.calculate_holding_amount('JPY')
    
    # 현재가치 및 손익률 계산
    usd_current_value = trading_system.calculate_current_value('USD', 
        usd_rate.current_rate if usd_rate else 0, usd_holding)
    jpy_current_value = trading_system.calculate_current_value('JPY', 
        jpy_rate.current_rate if jpy_rate else 0, jpy_holding)
    
    html = render_template('rate_cards.html', 
                         usd_rate=usd_rate,
                         jpy_rate=jpy_rate,
                         usd_settings=usd_settings,
                         jpy_settings=jpy_settings,
                         usd_holding=usd_holding,
                         jpy_holding=jpy_holding,
                         usd_current_value=usd_current_value,
                         jpy_current_value=jpy_current_value)
    
    return html

@app.route('/settings', methods=['POST'])
def save_settings():
    # USD 설정 저장
    usd_settings = {
        'rate_increments': [
            int(request.form['usd_rate_increment_1']),
            int(request.form['usd_rate_increment_2']),
            int(request.form['usd_rate_increment_3'])
        ],
        'stop_loss_gap': int(request.form['usd_stop_loss_gap']),
        'default_amount': int(request.form['usd_default_amount']),
        'buy_drop_threshold': int(request.form['usd_buy_drop_threshold'])
    }
    
    # JPY 설정 저장
    jpy_settings = {
        'rate_increments': [
            int(request.form['jpy_rate_increment_1']),
            int(request.form['jpy_rate_increment_2']),
            int(request.form['jpy_rate_increment_3'])
        ],
        'stop_loss_gap': int(request.form['jpy_stop_loss_gap']),
        'default_amount': int(request.form['jpy_default_amount']),
        'buy_drop_threshold': int(request.form['jpy_buy_drop_threshold'])
    }
    
    # 설정 업데이트
    trading_system.update_currency_settings('USD', **usd_settings)
    trading_system.update_currency_settings('JPY', **jpy_settings)
    
    flash('설정이 저장되었습니다.', 'success')
    return redirect(url_for('settings'))

if __name__ == '__main__':
    app.run(debug=True) 