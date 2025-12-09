# tools/technical.py
# Technical analysis indicators tools

from langchain.tools import tool
import yfinance as yf
import ta

@tool
def get_ta_data(ticker: str) -> str:
    """
    Calculates 1-year technical indicator data for a stock.
    (Includes momentum, volume, volatility, trend indicators)
    Args:
        ticker (str): Stock ticker to analyze (e.g., '005930' or 'AAPL').
    Returns:
        str: Full technical indicator time series data and current signal summary.
    """
    try:
        # 1. Check if ticker is numeric only (determine if Korean stock)
        is_korean_stock = ticker.isdigit()

        # 2. Prepare ticker for yfinance
        yf_ticker = ticker  # Default is the provided ticker
        if is_korean_stock:
            yf_ticker = f"{ticker}.KS"  # Append ".KS" for Korean stocks

        # 3. Create stock object with yfinance
        stock = yf.Ticker(yf_ticker)

        # 4. Fetch 1-year historical data
        hist = stock.history(period="1y")

        # 5. Check if data is empty
        if hist.empty:
            return f"Technical indicator calculation failed: no historical data ({ticker})"

        # 6. Start calculating technical indicators (with error handling for each)
        failed_indicators = []  # List of failed indicators

        # === Momentum Indicators (Momentum Indicators) ===
        try:
            hist['RSI'] = ta.momentum.rsi(hist['Close'], window=14)
        except Exception as e:
            failed_indicators.append(f"RSI: {e}")

        try:
            hist['TSI'] = ta.momentum.tsi(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"TSI: {e}")

        try:
            hist['UO'] = ta.momentum.ultimate_oscillator(hist['High'], hist['Low'], hist['Close'])
        except Exception as e:
            failed_indicators.append(f"UO: {e}")

        try:
            hist['Stoch'] = ta.momentum.stoch(hist['High'], hist['Low'], hist['Close'])
        except Exception as e:
            failed_indicators.append(f"Stoch: {e}")

        try:
            hist['StochRSI'] = ta.momentum.stochrsi(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"StochRSI: {e}")

        try:
            hist['WR'] = ta.momentum.williams_r(hist['High'], hist['Low'], hist['Close'])
        except Exception as e:
            failed_indicators.append(f"WR: {e}")

        try:
            hist['ROC'] = ta.momentum.roc(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"ROC: {e}")

        try:
            hist['AO'] = ta.momentum.awesome_oscillator(hist['High'], hist['Low'])
        except Exception as e:
            failed_indicators.append(f"AO: {e}")

        try:
            hist['KAMA'] = ta.momentum.kama(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"KAMA: {e}")

        try:
            hist['PPO'] = ta.momentum.ppo(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"PPO: {e}")

        # === Volume Indicators (Volume Indicators) ===
        try:
            hist['ADI'] = ta.volume.acc_dist_index(hist['High'], hist['Low'], hist['Close'], hist['Volume'])
        except Exception as e:
            failed_indicators.append(f"ADI: {e}")

        try:
            hist['OBV'] = ta.volume.on_balance_volume(hist['Close'], hist['Volume'])
        except Exception as e:
            failed_indicators.append(f"OBV: {e}")

        try:
            hist['CMF'] = ta.volume.chaikin_money_flow(hist['High'], hist['Low'], hist['Close'], hist['Volume'])
        except Exception as e:
            failed_indicators.append(f"CMF: {e}")

        try:
            hist['FI'] = ta.volume.force_index(hist['Close'], hist['Volume'])
        except Exception as e:
            failed_indicators.append(f"FI: {e}")

        try:
            hist['MFI'] = ta.volume.money_flow_index(hist['High'], hist['Low'], hist['Close'], hist['Volume'])
        except Exception as e:
            failed_indicators.append(f"MFI: {e}")

        try:
            hist['EOM'] = ta.volume.ease_of_movement(hist['High'], hist['Low'], hist['Volume'])
        except Exception as e:
            failed_indicators.append(f"EOM: {e}")

        try:
            hist['VPT'] = ta.volume.volume_price_trend(hist['Close'], hist['Volume'])
        except Exception as e:
            failed_indicators.append(f"VPT: {e}")

        try:
            hist['NVI'] = ta.volume.negative_volume_index(hist['Close'], hist['Volume'])
        except Exception as e:
            failed_indicators.append(f"NVI: {e}")

        try:
            hist['VWAP'] = ta.volume.volume_weighted_average_price(hist['High'], hist['Low'], hist['Close'], hist['Volume'])
        except Exception as e:
            failed_indicators.append(f"VWAP: {e}")

        # === Volatility Indicators (Volatility Indicators) ===
        try:
            hist['ATR'] = ta.volatility.average_true_range(hist['High'], hist['Low'], hist['Close'])
        except Exception as e:
            failed_indicators.append(f"ATR: {e}")

        try:
            bb = ta.volatility.BollingerBands(hist['Close'])
            hist['BB_High'] = bb.bollinger_hband()
            hist['BB_Mid'] = bb.bollinger_mavg()
            hist['BB_Low'] = bb.bollinger_lband()
        except Exception as e:
            failed_indicators.append(f"Bollinger Bands: {e}")

        try:
            kc = ta.volatility.KeltnerChannel(hist['High'], hist['Low'], hist['Close'])
            hist['KC_High'] = kc.keltner_channel_hband()
            hist['KC_Mid'] = kc.keltner_channel_mband()
            hist['KC_Low'] = kc.keltner_channel_lband()
        except Exception as e:
            failed_indicators.append(f"Keltner Channel: {e}")

        try:
            dc = ta.volatility.DonchianChannel(hist['High'], hist['Low'], hist['Close'])
            hist['DC_High'] = dc.donchian_channel_hband()
            hist['DC_Mid'] = dc.donchian_channel_mband()
            hist['DC_Low'] = dc.donchian_channel_lband()
        except Exception as e:
            failed_indicators.append(f"Donchian Channel: {e}")

        try:
            hist['UI'] = ta.volatility.ulcer_index(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"UI: {e}")

        # === Trend Indicators (Trend Indicators) ===
        try:
            hist['SMA_20'] = ta.trend.sma_indicator(hist['Close'], window=20)
            hist['SMA_50'] = ta.trend.sma_indicator(hist['Close'], window=50)
        except Exception as e:
            failed_indicators.append(f"SMA: {e}")

        try:
            hist['EMA_12'] = ta.trend.ema_indicator(hist['Close'], window=12)
            hist['EMA_26'] = ta.trend.ema_indicator(hist['Close'], window=26)
        except Exception as e:
            failed_indicators.append(f"EMA: {e}")

        try:
            hist['WMA_20'] = ta.trend.wma_indicator(hist['Close'], window=20)
        except Exception as e:
            failed_indicators.append(f"WMA: {e}")

        try:
            macd = ta.trend.MACD(hist['Close'])
            hist['MACD'] = macd.macd()
            hist['MACD_Signal'] = macd.macd_signal()
            hist['MACD_Hist'] = macd.macd_diff()
        except Exception as e:
            failed_indicators.append(f"MACD: {e}")

        try:
            hist['ADX'] = ta.trend.adx(hist['High'], hist['Low'], hist['Close'])
        except Exception as e:
            failed_indicators.append(f"ADX: {e}")

        try:
            hist['VI_Pos'] = ta.trend.vortex_indicator_pos(hist['High'], hist['Low'], hist['Close'])
            hist['VI_Neg'] = ta.trend.vortex_indicator_neg(hist['High'], hist['Low'], hist['Close'])
        except Exception as e:
            failed_indicators.append(f"Vortex: {e}")

        try:
            hist['TRIX'] = ta.trend.trix(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"TRIX: {e}")

        try:
            hist['MI'] = ta.trend.mass_index(hist['High'], hist['Low'])
        except Exception as e:
            failed_indicators.append(f"MI: {e}")

        try:
            hist['CCI'] = ta.trend.cci(hist['High'], hist['Low'], hist['Close'])
        except Exception as e:
            failed_indicators.append(f"CCI: {e}")

        try:
            hist['DPO'] = ta.trend.dpo(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"DPO: {e}")

        try:
            hist['KST'] = ta.trend.kst(hist['Close'])
            hist['KST_Signal'] = ta.trend.kst_sig(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"KST: {e}")

        try:
            ich = ta.trend.IchimokuIndicator(hist['High'], hist['Low'])
            hist['Ichimoku_A'] = ich.ichimoku_a()
            hist['Ichimoku_B'] = ich.ichimoku_b()
        except Exception as e:
            failed_indicators.append(f"Ichimoku: {e}")

        try:
            hist['PSAR'] = ta.trend.psar_down(hist['High'], hist['Low'], hist['Close'])
        except Exception as e:
            failed_indicators.append(f"PSAR: {e}")

        try:
            hist['STC'] = ta.trend.stc(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"STC: {e}")

        try:
            hist['Aroon_Up'] = ta.trend.aroon_up(hist['High'], hist['Low'])
            hist['Aroon_Down'] = ta.trend.aroon_down(hist['High'], hist['Low'])
        except Exception as e:
            failed_indicators.append(f"Aroon: {e}")

        # === Other Indicators (Others) ===
        try:
            hist['DR'] = ta.others.daily_return(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"DR: {e}")

        try:
            hist['DLR'] = ta.others.daily_log_return(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"DLR: {e}")

        try:
            hist['CR'] = ta.others.cumulative_return(hist['Close'])
        except Exception as e:
            failed_indicators.append(f"CR: {e}")

        # 7. Compile summary information for AI
        summary = f"--- Technical Indicator Analysis ({ticker}) ---\n"
        summary += f"Data Period: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}\n"
        summary += f"Total Trading Days: {len(hist)}\n\n"

        # Report failed indicators first if any
        if failed_indicators:
            summary += "!!! Failed to Calculate Indicators !!!\n"
            for failure in failed_indicators:
                summary += f"  - {failure}\n"
            summary += "\n"

        # Current Indicator Values (Latest Trading Day)
        summary += "=== Current Indicator Values (Latest Trading Day) ===\n"
        latest = hist.iloc[-1]

        summary += f"\n[Momentum Indicators]\n"
        if 'RSI' in hist.columns:
            summary += f"RSI: {latest['RSI']:.2f} (overbought>70, oversold<30)\n"
        if 'TSI' in hist.columns:
            summary += f"TSI: {latest['TSI']:.2f}\n"
        if 'UO' in hist.columns:
            summary += f"UO (Ultimate Oscillator): {latest['UO']:.2f}\n"
        if 'Stoch' in hist.columns:
            summary += f"Stochastic: {latest['Stoch']:.2f}\n"
        if 'StochRSI' in hist.columns:
            summary += f"Stochastic RSI: {latest['StochRSI']:.2f}\n"
        if 'WR' in hist.columns:
            summary += f"Williams %R: {latest['WR']:.2f}\n"
        if 'ROC' in hist.columns:
            summary += f"ROC (Rate of Change): {latest['ROC']:.2f}%\n"
        if 'AO' in hist.columns:
            summary += f"AO (Awesome Oscillator): {latest['AO']:.2f}\n"
        if 'KAMA' in hist.columns:
            summary += f"KAMA: {latest['KAMA']:.2f}\n"
        if 'PPO' in hist.columns:
            summary += f"PPO: {latest['PPO']:.2f}\n"

        summary += f"\n[Volume Indicators]\n"
        if 'ADI' in hist.columns:
            summary += f"ADI (Acc/Dist Index): {latest['ADI']:.0f}\n"
        if 'OBV' in hist.columns:
            summary += f"OBV (On-Balance Volume): {latest['OBV']:.0f}\n"
        if 'CMF' in hist.columns:
            summary += f"CMF (Chaikin Money Flow): {latest['CMF']:.4f}\n"
        if 'FI' in hist.columns:
            summary += f"FI (Force Index): {latest['FI']:.2f}\n"
        if 'MFI' in hist.columns:
            summary += f"MFI (Money Flow Index): {latest['MFI']:.2f}\n"
        if 'EOM' in hist.columns:
            summary += f"EOM (Ease of Movement): {latest['EOM']:.4f}\n"
        if 'VPT' in hist.columns:
            summary += f"VPT (Volume-Price Trend): {latest['VPT']:.0f}\n"
        if 'NVI' in hist.columns:
            summary += f"NVI (Negative Volume Index): {latest['NVI']:.2f}\n"
        if 'VWAP' in hist.columns:
            summary += f"VWAP: {latest['VWAP']:.2f}\n"

        summary += f"\n[Volatility Indicators]\n"
        if 'ATR' in hist.columns:
            summary += f"ATR (Average True Range): {latest['ATR']:.2f}\n"
        if all(col in hist.columns for col in ['BB_High', 'BB_Mid', 'BB_Low']):
            summary += f"Bollinger Bands: High={latest['BB_High']:.2f}, Mid={latest['BB_Mid']:.2f}, Low={latest['BB_Low']:.2f}\n"
        if all(col in hist.columns for col in ['KC_High', 'KC_Mid', 'KC_Low']):
            summary += f"Keltner Channel: High={latest['KC_High']:.2f}, Mid={latest['KC_Mid']:.2f}, Low={latest['KC_Low']:.2f}\n"
        if all(col in hist.columns for col in ['DC_High', 'DC_Mid', 'DC_Low']):
            summary += f"Donchian Channel: High={latest['DC_High']:.2f}, Mid={latest['DC_Mid']:.2f}, Low={latest['DC_Low']:.2f}\n"
        if 'UI' in hist.columns:
            summary += f"Ulcer Index: {latest['UI']:.2f}\n"

        summary += f"\n[Trend Indicators]\n"
        if 'SMA_20' in hist.columns and 'SMA_50' in hist.columns:
            summary += f"SMA: 20-day={latest['SMA_20']:.2f}, 50-day={latest['SMA_50']:.2f}\n"
        if 'EMA_12' in hist.columns and 'EMA_26' in hist.columns:
            summary += f"EMA: 12-day={latest['EMA_12']:.2f}, 26-day={latest['EMA_26']:.2f}\n"
        if 'WMA_20' in hist.columns:
            summary += f"WMA (20-day): {latest['WMA_20']:.2f}\n"
        if all(col in hist.columns for col in ['MACD', 'MACD_Signal', 'MACD_Hist']):
            summary += f"MACD: {latest['MACD']:.4f}, Signal: {latest['MACD_Signal']:.4f}, Histogram: {latest['MACD_Hist']:.4f}\n"
        if 'ADX' in hist.columns:
            summary += f"ADX (trend strength): {latest['ADX']:.2f} (>25 strong)\n"
        if 'VI_Pos' in hist.columns and 'VI_Neg' in hist.columns:
            summary += f"Vortex: Positive={latest['VI_Pos']:.2f}, Negative={latest['VI_Neg']:.2f}\n"
        if 'TRIX' in hist.columns:
            summary += f"TRIX: {latest['TRIX']:.4f}\n"
        if 'MI' in hist.columns:
            summary += f"Mass Index: {latest['MI']:.2f}\n"
        if 'CCI' in hist.columns:
            summary += f"CCI (Commodity Channel Index): {latest['CCI']:.2f}\n"
        if 'DPO' in hist.columns:
            summary += f"DPO (Detrended Price Osc): {latest['DPO']:.2f}\n"
        if 'KST' in hist.columns and 'KST_Signal' in hist.columns:
            summary += f"KST: {latest['KST']:.2f}, Signal: {latest['KST_Signal']:.2f}\n"
        if 'Ichimoku_A' in hist.columns and 'Ichimoku_B' in hist.columns:
            summary += f"Ichimoku: A={latest['Ichimoku_A']:.2f}, B={latest['Ichimoku_B']:.2f}\n"
        if 'PSAR' in hist.columns:
            summary += f"Parabolic SAR: {latest['PSAR']:.2f}\n"
        if 'STC' in hist.columns:
            summary += f"STC (Schaff Trend Cycle): {latest['STC']:.2f}\n"
        if 'Aroon_Up' in hist.columns and 'Aroon_Down' in hist.columns:
            summary += f"Aroon: Up={latest['Aroon_Up']:.2f}, Down={latest['Aroon_Down']:.2f}\n"

        summary += f"\n[Other Indicators]\n"
        if 'DR' in hist.columns:
            summary += f"Daily Return (DR): {latest['DR']:.4f}\n"
        if 'DLR' in hist.columns:
            summary += f"Daily Log Return (DLR): {latest['DLR']:.4f}\n"
        if 'CR' in hist.columns:
            summary += f"Cumulative Return (CR): {latest['CR']:.4f}\n"

        # Recent 10-Day Trend (Key Indicators) - Select only existing columns
        summary += "\n\n=== Recent 10-Day Trend (Key Indicators) ===\n"
        key_indicators = ['RSI', 'MACD', 'ADX', 'OBV', 'ATR', 'CCI']
        available_indicators = [col for col in key_indicators if col in hist.columns]
        if available_indicators:
            recent = hist[available_indicators].tail(10)
            summary += recent.to_string()
        else:
            summary += "(Cannot calculate key indicators)\n"

        # Full time series data
        summary += "\n\n=== Full Time Series Data (1 Year) ===\n"
        summary += "(Full period data for all technical indicators)\n\n"

        # Select only technical indicator columns (exclude OHLCV)
        indicator_cols = [col for col in hist.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']]
        if indicator_cols:
            summary += hist[indicator_cols].to_string()
        else:
            summary += "(No calculated technical indicators)\n"

        return summary

    except Exception as e:
        # Report error to AI
        return f"Error calculating technical indicators ({ticker}): {e}"
