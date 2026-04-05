
import re
with open('logs/last_checkout_fail.html', 'r', encoding='utf-8') as f:
    text = f.read()
for match in re.findall(r'href=[\"''\]([^>]+)[\"''\]', text):
    print(match)

