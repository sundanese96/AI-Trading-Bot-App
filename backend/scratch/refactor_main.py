import os

file_path = '/media/sun/DATA/sentix-ai-crypto-simulator/backend/main.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Auth routes to remove: from '# Persistent Session Management' up to '# Register Sentix UI'
start_auth = content.find('# Persistent Session Management')
end_auth = content.find('# Register Sentix UI')
if start_auth != -1 and end_auth != -1:
    content = content[:start_auth] + content[end_auth:]

# Market routes: from '@app.get("/api/market-data")' up to 'class StartSessionRequest'
start_market = content.find('@app.get("/api/market-data")')
end_market = content.find('class StartSessionRequest(BaseModel):')
if start_market != -1 and end_market != -1:
    content = content[:start_market] + content[end_market:]

# Live-sim & Trades: from 'class StartSessionRequest(BaseModel):' up to '# ML Model Endpoints'
start_sim = content.find('class StartSessionRequest(BaseModel):')
end_sim = content.find('# ML Model Endpoints')
if start_sim != -1 and end_sim != -1:
    content = content[:start_sim] + content[end_sim:]

# Add router includes
target_include = "# Register Sentix UI compatibility adapter routes (takes priority)\n"
include_str = """
from backend.api.auth import router as auth_router
app.include_router(auth_router)

from backend.api.market import router as market_router
app.include_router(market_router)

from backend.api.simulation import router as simulation_router
app.include_router(simulation_router)

from backend.api.trades import router as trades_router
app.include_router(trades_router)

"""
if target_include in content:
    content = content.replace(target_include, include_str + target_include)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Safely refactored main.py.")
