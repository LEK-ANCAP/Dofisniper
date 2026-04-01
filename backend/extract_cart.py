import re

with open(r'logs\last_checkout_fail.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("--- Icons ---")
icons = re.finditer(r'<i[^>]*>', text)
cart_icons = set()
for m in icons:
    if 'cart' in m.group(0).lower():
        cart_icons.add(m.group(0))
for icon in cart_icons:
    print(icon)

print("\n--- Around quantity ---")
# Try to find the cart icon and what tag wraps it
matches = re.finditer(r'<([a-z0-9]+)[^>]*>\s*<i[^>]*class="[^"]*cart[^"]*"[^>]*>\s*</i>\s*</\1>', text, re.IGNORECASE)
for m in matches:
    print('Wrapper around cart icon:', m.group(0))

print("\n--- Any cart or buy or shop elements ---")
for word in ['cart', 'buy', 'shop']:
    wrapper = re.findall(r'<div[^>]*class="[^"]*' + word + r'[^"]*"[^>]*>', text)
    if wrapper:
        print(f"Found divs with {word}:", set(wrapper))
    btn = re.findall(r'<button[^>]*class="[^"]*' + word + r'[^"]*"[^>]*>', text)
    if btn:
        print(f"Found buttons with {word}:", set(btn))
