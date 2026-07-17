import os
import re

filepath = "/home/x/AI-Trading-Bot-App/backend/services/scraper.py"
with open(filepath, "r") as f:
    content = f.read()

target = '''    url = "https://www.forexfactory.com/ffcal_week_this.xml"'''
replacement = '''    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"'''

content = content.replace(target, replacement)

target_parse = '''                root = ET.fromstring(response.content)
                for event in root.findall("event"):
                    title = event.find("title").text if event.find("title") is not None else ""
                    country = event.find("country").text if event.find("country") is not None else ""
                    impact = event.find("impact").text if event.find("impact") is not None else ""'''

replacement_parse = '''                events = response.json()
                for event in events:
                    title = event.get("title", "")
                    country = event.get("country", "")
                    impact = event.get("impact", "")'''

content = content.replace(target_parse, replacement_parse)

with open(filepath, "w") as f:
    f.write(content)
print("Patched scraper.py")
