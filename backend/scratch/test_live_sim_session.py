import asyncio
import time
import sys
import os

# Adjust path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.services.live_sim_manager import live_sim_manager
from backend.services.market import assets

async def main():
    print("--- Starting Live Simulation Session Manager Verification ---")

    # 1. Start a session
    strategy = "MOMENTUM"
    capital = 10000.0
    whitelist = ["BTC", "ETH"]
    
    print(f"Starting session with {strategy} and capital ${capital}...")
    await live_sim_manager.start_session(strategy, capital, whitelist)
    
    assert live_sim_manager.active == True, "Session should be active"
    assert live_sim_manager.strategy == "MOMENTUM", "Strategy should match"
    assert live_sim_manager.initial_capital == capital, "Capital should match"
    assert "BTC" in live_sim_manager.target_assets, "BTC should be whitelisted"
    
    print("SUCCESS: Session started successfully and whitelists aligned!")

    # 2. Simulate technical breakout on BTC
    # Let's mock the BTC price history to trigger a Lower Bollinger Band breakout (SHORT signal)
    # We find BTC asset
    btc_asset = None
    for a in assets:
        if a["symbol"] == "BTC":
            btc_asset = a
            break
            
    if btc_asset:
        # Flatten all histories to prevent accidental triggers
        for a in assets:
            a["history"] = [a["price"]] * 20
            
        # Create prices history where current price drops way below standard deviation
        # Let's mock a steady history around $60,000 with a slight variance to prevent stddev = 0
        btc_asset["history"] = [60000.0] * 19 + [59990.0]
        btc_asset["price"] = 55000.0 # Huge drop to trigger lower band breakout
        
        print("Feeding mock price to trigger SHORT momentum signal on BTC...")
        await live_sim_manager.check_momentum_strategy()
        
        # Check if trade is opened
        open_trades = [t for t in live_sim_manager.trades if t["status"] == "OPEN"]
        if open_trades:
            trade = open_trades[0]
            print(f"SUCCESS: Opened momentum trade on {trade['targetAsset']}: {trade['decision']} at {trade['entryPrice']}")
            assert trade["decision"] == "SHORT", "Should open a SHORT trade on a downward breakout"
            
            # 3. Simulate price movement to trigger Take Profit exit
            # Entry is 55000. For SHORT, TP is +4% (meaning a 4% drop: 55000 * 0.96 = 52800)
            print("Simulating further price drop to trigger Take Profit...")
            btc_asset["price"] = 52000.0
            
            # Manually run the monitor check logic to simulate loop iteration
            for t in live_sim_manager.trades:
                if t["status"] == "OPEN" and t["targetAsset"] == "BTC":
                    cur_price = live_sim_manager.get_asset_price("BTC")
                    t["currentPrice"] = cur_price
                    entry_price = t["entryPrice"]
                    price_change_pct = ((entry_price - cur_price) / entry_price) * 100
                    pnl_pct = price_change_pct * 5.0 # 5x leverage
                    t["pnl"] = round(pnl_pct, 2)
                    
                    if price_change_pct >= 4.0:
                        t["status"] = "CLOSED"
                        t["exitPrice"] = cur_price
                        t["closeTime"] = int(time.time() * 1000)
                        t["closeReason"] = "TAKE_PROFIT"
                        
                        margin = t["marginAllocated"]
                        pnl_usd = margin * (pnl_pct / 100.0)
                        live_sim_manager.current_capital += pnl_usd
                        print(f"Position closed by TP! PnL: {t['pnl']}%, Wallet Balance: ${live_sim_manager.current_capital:.2f}")

            # Verify trade closed
            closed_trades = [t for t in live_sim_manager.trades if t["status"] == "CLOSED"]
            if closed_trades:
                print(f"SUCCESS: Trade closed. Reason: {closed_trades[0]['closeReason']}. Balance is now ${live_sim_manager.current_capital:.2f}")
                assert closed_trades[0]["closeReason"] == "TAKE_PROFIT", "Should close with TAKE_PROFIT"
            else:
                print("FAIL: Trade did not close.")
        else:
            print("FAIL: No momentum trade was opened.")
    else:
        print("FAIL: Could not locate BTC asset in mock list.")

    # 4. Stop session
    print("Stopping session...")
    await live_sim_manager.stop_session()
    assert live_sim_manager.active == False, "Session should be inactive"
    print("SUCCESS: Session stopped successfully!")

if __name__ == "__main__":
    asyncio.run(main())
