import json

with open("temp_details_utf8.json", "r", encoding="utf-8-sig") as f:
    data = json.load(f)

for k, v in data.get("data", {}).items():
    if isinstance(v, list):
        print(f"Array {k} length: {len(v)}")
        if k == "goodsParameterList" or k == "specProductList":
            if v: print(f"First item of {k}: {json.dumps(v[0], indent=2)}")
        if k == "specValues" or k == "specProductList":
            for item in v:
                print(f"--> {json.dumps(item)}")
