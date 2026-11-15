"""Workbenchで「'ID','商品名','カテゴリー','説明文'」の形でコピーしたデータを JSON に変換する。

使い方: python3 scripts/parse_quoted.py 入力.txt 出力.json
説明文の中に改行があっても、行頭が 'G0000',' で始まる行を1件の始まりとして読む。
"""
import json
import re
import sys

src, out = sys.argv[1], sys.argv[2]
text = open(src, encoding='utf-8').read()
chunks = re.split(r"(?m)^(?='G\d{4}',')", text)
rows = []
for c in chunks:
    c = c.strip()
    if not c:
        continue
    if not (c.startswith("'") and c.endswith("'")):
        raise ValueError('形がおかしい行があります: ' + c[:40])
    parts = c[1:-1].split("','", 3)
    if len(parts) != 4:
        raise ValueError('列の数が4つではありません: ' + c[:40])
    pid, name, category, description = parts
    rows.append({'product_id': pid, 'product_name': name, 'category': category, 'description': description})

json.dump(rows, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{len(rows)}件を書き出しました: {rows[0]["product_id"]}〜{rows[-1]["product_id"]}')
