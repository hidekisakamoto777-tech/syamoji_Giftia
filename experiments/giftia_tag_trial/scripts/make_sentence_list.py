"""正解データ用の200件を取り分け、残りの商品から「文の種類の一覧」を作って Excel に書き出す。

使い方: python3 scripts/make_sentence_list.py data/products_all.json out/sentence_list.xlsx
・200件はランダムに選ぶ。SEED を変えなければ、何度実行しても同じ200件になる。
・一覧は、決まり文句を取り除いたあとの文を、出てくる商品数の多い順に並べる。
"""
import collections
import json
import os
import random
import re
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tag_rule_clean import BOILER, SCENE

SEED = 20261114
N_ANSWER = 200

src, out = sys.argv[1], sys.argv[2]
products = json.load(open(src, encoding='utf-8'))

# tag_rules4.py から言い回しの一覧（RULES）だけを読み込む（判定の本体は動かさない）
rules_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tag_rules4.py'), encoding='utf-8').read()
ns = {}
exec(rules_src[rules_src.index('RULES = {'):rules_src.index('def judge')], ns)
RULES = ns['RULES']
TAG_LABELS = [RULES[t]['label'] for t in RULES]


def split_sentences(desc):
    """tag_rule_clean.clean と同じ決まりで、残す文と取り除く文（理由つき）に分ける"""
    kept, removed = [], []
    for i, s in enumerate(re.split(r'[。\n]', desc)):
        s = s.strip()
        if not s or s.startswith('【'):
            continue
        if i > 0 and '好き' not in s:
            hit = [b for b in BOILER if b in s]
            m = SCENE.search(s)
            if hit or m:
                removed.append((s + '。', '・'.join(hit + ([m.group(0)] if m else []))))
                continue
        kept.append(s + '。')
    return kept, removed


def rule_hits(sentence):
    out = []
    for t, r in RULES.items():
        for kind, name in (('strong', '確実'), ('medium', '弱い'), ('exclude', '除外')):
            for k in r[kind]:
                if k in sentence:
                    out.append(f"{r['label']}（{name}）：{k}")
    return ' ／ '.join(out)


# ① 正解データ用の200件を取り分ける
rng = random.Random(SEED)
answer = sorted(rng.sample(products, N_ANSWER), key=lambda p: p['product_id'])
answer_ids = {p['product_id'] for p in answer}
rest = [p for p in products if p['product_id'] not in answer_ids]

# ② 残りの商品から、文の種類を数える（1商品の中で同じ文が2回出ても1と数える）
kept_count, kept_cat, kept_ex = collections.Counter(), collections.defaultdict(collections.Counter), collections.defaultdict(list)
rem_count, rem_reason = collections.Counter(), {}
for p in rest:
    kept, removed = split_sentences(p['description'])
    for s in set(kept):
        kept_count[s] += 1
        kept_cat[s][p['category']] += 1
        if len(kept_ex[s]) < 3:
            kept_ex[s].append(f"{p['product_id']} {p['product_name']}")
    for s, why in set(removed):
        rem_count[s] += 1
        rem_reason[s] = why

# ③ Excel に書き出す
HEAD = Font(bold=True)
HEAD_FILL = PatternFill('solid', fgColor='DDEBF7')
INPUT_FILL = PatternFill('solid', fgColor='FFF2CC')
WRAP = Alignment(wrap_text=True, vertical='top')


def sheet(wb, title, header, widths, rows, input_cols=()):
    ws = wb.create_sheet(title)
    ws.append(header)
    for c, w in zip(ws[1], widths):
        c.font, c.fill, c.alignment = HEAD, HEAD_FILL, WRAP
        ws.column_dimensions[c.column_letter].width = w
    for r in rows:
        ws.append(r)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = WRAP
            if c.column in input_cols:
                c.fill = INPUT_FILL
    ws.freeze_panes = 'C2'
    ws.auto_filter.ref = ws.dimensions
    return ws


wb = Workbook()
guide = wb.active
guide.title = '使い方'
lines = [
    'タグの言い回しを決めるための一覧（試作・班の合意前の作業用）',
    '',
    f'元データ：products 全{len(products)}件（{products[0]["product_id"]}〜{products[-1]["product_id"]}）',
    f'正解データ用に {N_ANSWER}件をランダムに取り分けた（乱数の種 {SEED}。同じ種なら何度作っても同じ200件）。',
    f'一覧は、残りの{len(rest)}件だけから作った。取り分けた200件の説明文は、言い回しづくりに使わない。',
    '',
    '【シート】',
    f'・文の種類：決まり文句を取り除いたあとの文 {len(kept_count)}種類を、出てくる商品数の多い順に並べた。',
    '　黄色の列に、タグと「確実／弱い／除外」を書き込む。今のルールで当たる言い回しは「今のルールで当たる言い回し」列に出している。',
    f'・取り除いた決まり文句：のし・配送・年代などで取り除いた文 {len(rem_count)}種類と、取り除いた理由（当たった言葉）。',
    '　タグの手がかりになる文が消えていないかを確かめる。消してはいけない文があれば「メモ」列に書く。',
    f'・正解データ用200件：人が〇×を付ける商品。担当（1〜4）ごとに50件ずつ。黄色の列に〇か×を入れる。',
    '',
    '【決まり】',
    '・確実：その言い回しがあれば、そのタグを付けてよい。',
    '・弱い：それだけでは決めきれない（要確認にする）。',
    '・除外：その言い回しがあれば、そのタグは付けない。',
    '・タグの名前と説明文は、要件定義書5.2「タグの一覧」のとおり。',
]
for ln in lines:
    guide.append([ln])
guide.column_dimensions['A'].width = 120
guide['A1'].font = Font(bold=True, size=13)

rows = []
for i, (s, n) in enumerate(sorted(kept_count.items(), key=lambda x: (-x[1], x[0])), 1):
    cats = '・'.join(f'{c} {k}' for c, k in kept_cat[s].most_common(3))
    rows.append([i, s, n, cats, '\n'.join(kept_ex[s]), rule_hits(s), '', '', ''])
sheet(wb, '文の種類', ['No', '文', '出てくる商品数', '多いカテゴリー（上位3）', '例の商品（最大3つ）',
                      '今のルールで当たる言い回し', '決める：タグ', '決める：確実／弱い／除外', 'メモ'],
      [6, 60, 10, 28, 40, 40, 22, 14, 30], rows, input_cols=(7, 8, 9))

rows = [[i, s, n, rem_reason[s], ''] for i, (s, n) in
        enumerate(sorted(rem_count.items(), key=lambda x: (-x[1], x[0])), 1)]
sheet(wb, '取り除いた決まり文句', ['No', '文', '出てくる商品数', '取り除いた理由（当たった言葉）', 'メモ'],
      [6, 60, 10, 30, 30], rows, input_cols=(5,))

rows = [[i, (i - 1) // (N_ANSWER // 4) + 1, p['product_id'], p['product_name'], p['category'], p['description']]
        + [''] * len(TAG_LABELS) + ['', ''] for i, p in enumerate(answer, 1)]
tag_start = 7
ws = sheet(wb, '正解データ用200件', ['No', '担当（1〜4）', '商品ID', '商品名', 'カテゴリー', '説明文（そのまま）']
           + TAG_LABELS + ['確認した人', 'メモ'],
           [6, 8, 8, 30, 12, 60] + [12] * len(TAG_LABELS) + [12, 30], rows,
           input_cols=tuple(range(tag_start, tag_start + len(TAG_LABELS) + 2)))
dv = DataValidation(type='list', formula1='"〇,×"', allow_blank=True)
ws.add_data_validation(dv)
first, last = ws.cell(2, tag_start).coordinate, ws.cell(N_ANSWER + 1, tag_start + len(TAG_LABELS) - 1).coordinate
dv.add(f'{first}:{last}')

os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
wb.save(out)
print(f'正解データ用 {len(answer)}件 / 一覧に使った商品 {len(rest)}件')
print(f'文の種類 {len(kept_count)} / 取り除いた決まり文句 {len(rem_count)}')
print('書き出し:', out)
