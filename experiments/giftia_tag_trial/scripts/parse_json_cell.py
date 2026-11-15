"""JSON_ARRAYAGG でまとめて取り出した products（1マス分のJSON）を、商品ID順の JSON にする。

使い方: python3 scripts/parse_json_cell.py 入力.txt 出力.json
取り出しに使ったSQL:
SELECT JSON_ARRAYAGG(JSON_OBJECT('product_id', product_id, 'product_name', product_name,
  'category', category, 'description', description)) AS all_products FROM products;
"""
import json
import sys

src, out = sys.argv[1], sys.argv[2]
text = open(src, encoding='utf-8').read().strip()
if text.startswith("'") and text.endswith("'"):  # コピーしたときに外側に付く ' を外す
    text = text[1:-1]
rows = json.loads(text)
cols = ['product_id', 'product_name', 'category', 'description']
rows = sorted(({c: r[c] for c in cols} for r in rows), key=lambda r: r['product_id'])

ids = [r['product_id'] for r in rows]
if len(set(ids)) != len(ids):
    raise ValueError('同じ商品IDが2回以上出てきます')

json.dump(rows, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{len(rows)}件を書き出しました: {ids[0]}〜{ids[-1]}')
