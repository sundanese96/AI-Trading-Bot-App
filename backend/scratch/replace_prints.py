import os
import re

def replace_prints_in_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # We need to insert the logger import at the top if it's not there
    if "from backend.core.logger import logger" not in content:
        # Find the first import and insert it before it
        import_match = re.search(r'^(import |from )', content, flags=re.MULTILINE)
        if import_match:
            insert_pos = import_match.start()
            content = content[:insert_pos] + "from backend.core.logger import logger\n" + content[insert_pos:]
        else:
            content = "from backend.core.logger import logger\n\n" + content

    # Replace print("something") with logger.info("something")
    # We will use a regex that handles basic print statements
    # Pattern explanation: matches `print(` followed by anything until the matching closing parenthesis, but it's tricky with nested parens.
    # Simple regex for simple prints: print(f"...") or print("...")
    
    # A simple but effective regex that catches print( followed by string or formatted string
    # Replace `print(` with `logger.info(` for lines starting with whitespace and print(
    # We have to be careful not to replace prints inside multi-line strings, but in this codebase it's mostly single line prints.
    
    lines = content.split('\n')
    new_lines = []
    replaced_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("print(") and stripped.endswith(")"):
            # It's a simple print line
            # We assume it's info or error depending on the word "Error" or "Failed"
            if "error" in stripped.lower() or "failed" in stripped.lower():
                line = line.replace("print(", "logger.error(", 1)
            elif "warning" in stripped.lower():
                line = line.replace("print(", "logger.warning(", 1)
            else:
                line = line.replace("print(", "logger.info(", 1)
            replaced_count += 1
        new_lines.append(line)
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
        
    print(f"Replaced {replaced_count} prints in {file_path}")

replace_prints_in_file('/media/sun/DATA/sentix-ai-crypto-simulator/backend/main.py')
replace_prints_in_file('/media/sun/DATA/sentix-ai-crypto-simulator/backend/sentix_adapter.py')
