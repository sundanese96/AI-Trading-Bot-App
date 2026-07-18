with open("backend/main.py", "r") as f:
    lines = f.readlines()
    
start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.strip() == "hl_lower = headline.lower()":
        if i > 5 and lines[i-1].strip() == "":
            start_idx = i - 1
            break

for i in range(start_idx + 1, len(lines)):
    if "async def monitor_simulated_positions_loop(" in lines[i]:
        end_idx = i
        break
        
if end_idx > 0 and lines[end_idx-1].startswith("# Position"):
    end_idx -= 1

print(f"Replacing {start_idx} to {end_idx}")

with open("backend/scratch/refactored.py", "r") as f:
    refactored_content = f.read()

new_content = "".join(lines[:start_idx]) + "\n" + refactored_content + "\n\n" + "".join(lines[end_idx:])

with open("backend/main.py", "w") as f:
    f.write(new_content)

print("Injection Done")
