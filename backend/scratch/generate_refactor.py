with open("backend/main.py", "r") as f:
    lines = f.readlines()
    
# Find start of trigger_automated_trade_sim
start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith("async def trigger_automated_trade_sim("):
        start_idx = i
        break
        
for i in range(start_idx + 1, len(lines)):
    if line.startswith("async def monitor_simulated_positions_loop("):
        end_idx = i - 1
        break
        
print(f"Replacing {start_idx} to {end_idx}")

with open("backend/scratch/refactored.py", "r") as f:
    refactored_content = f.read()

new_content = "".join(lines[:start_idx - 1]) + "\n" + refactored_content + "\n" + "".join(lines[end_idx:])

with open("backend/main.py", "w") as f:
    f.write(new_content)

print("Done")
