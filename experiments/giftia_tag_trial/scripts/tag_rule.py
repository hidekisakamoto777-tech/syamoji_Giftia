# 遊び心・話のたね タグのルール判定（試作）
import sys, json, re, csv, statistics as st
P = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = sys.argv[2]

# ① 定型文：配送・包装・手続き、年代・シーン、使い道の決まり文句（「好き」を含む文は残す）
BOILER = ['のし', '納品書', 'ラッピング', 'メッセージカード', '名入れ', '刻印', '刺繍を承', 'まとめてのご注文',
          '会社宛て', '法人様', '20歳', 'お届けします', 'お届けいたします', 'お届け日', '保証書', 'かばんに入る',
          'コンパクトな箱', 'オフィスでもお渡し', '毎日の暮らしで使って', '日々の生活で活躍', '発送します',
          'お付けします', 'お付けできます', 'お選びいただけます', 'ご指定ください', 'ご記入ください', '承ります']
SCENE = re.compile(r'\d0代|プレゼントに|贈りもの(として|にも)|ギフトにおすすめ|選ばれています|プチギフトにも|ごあいさつ|職場へのちょっとした|喜ばれ')
def clean(desc):
    kept = []
    for i, s in enumerate(re.split(r'[。\n]', desc)):
        s = s.strip()
        if not s or s.startswith('【'):
            continue
        # 1文目は商品そのものの説明なので必ず残す
        if i > 0 and '好き' not in s and (any(b in s for b in BOILER) or SCENE.search(s)):
            continue
        kept.append(s)
    return '。'.join(kept) + ('。' if kept else '')

# ② 言い回しのルール
STRONG = ['遊び心', '箱を開けたときの驚き', 'ほかではあまり見かけない', 'ふざけた文面', '思わず笑って', '思わず二度見',
          '話しかけたくなる', '話のたね', 'ちょっと意外な贈りもの', 'SNSで話題', '会話が生まれる', 'とぼけた表情',
          '食品サンプルのよう', 'そっくりの形', '生きもののような形', '机の上がにぎやか', 'ふしぎな手ざわり',
          '通好み', '表情の違う動物']
MEDIUM = ['デザイナーが一つずつ', '少量生産', '個性の強い', 'クセのある味わい', '産地の個性', '個性がしっかり', '珍味',
          '置いておきたくなる形', '物語のある', '気分が上がる', '世界にひとつ', '手刺繍', '版画', '作家もの', '作家のサイン',
          '部屋の雰囲気が変わる', '限定醸造', '目にも楽しい', '昔の家電を思わせる', '表情は一つひとつ']
NEGATIVE = ['クセが少なく', '好みを選ばない', '贈る相手を選ばない', '年代を問わず', '定番の贈りもの', 'ギフトの定番']

rows = []
for p in P:
    text = p['product_name'] + ' ' + p['description']
    s = [k for k in STRONG if k in text]
    m = [k for k in MEDIUM if k in text]
    n = [k for k in NEGATIVE if k in text]
    if s and not n: judge = '自動'
    elif s or m: judge = '要確認'
    else: judge = 'なし'
    rows.append({**p, 'clean': clean(p['description']), 'strong': '・'.join(s), 'medium': '・'.join(m),
                 'negative': '・'.join(n), 'judge': judge})

before = [len(p['description']) for p in rows]; after = [len(p['clean']) for p in rows]
print(f"定型文の除去：平均 {st.mean(before):.0f}文字 → {st.mean(after):.0f}文字（{1-st.mean(after)/st.mean(before):.0%}減）, 空になった商品 {sum(a==0 for a in after)}件")
for j in ['自動', '要確認', 'なし']:
    L = [r for r in rows if r['judge'] == j]
    sales = sorted(r['sales_count'] for r in L)
    print(f"{j}: {len(L)}件  販売数0={sum(r['sales_count']==0 for r in L)}  レビュー0={sum(r['review_count']==0 for r in L)}  販売数中央値={sales[len(sales)//2]}")

cols = ['product_id','product_name','category','price','sales_count','review_count','judge','strong','medium','negative','clean']
with open(f'{OUT}/playful_tag_result.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols + ['check'], extrasaction='ignore')
    w.writeheader()
    for r in sorted(rows, key=lambda r: ['自動','要確認','なし'].index(r['judge'])):
        if r['judge'] != 'なし': w.writerow({**r, 'check': ''})
json.dump(rows, open(f'{OUT}/products_clean.json', 'w', encoding='utf-8'), ensure_ascii=False)
for j in ['自動', '要確認']:
    print(f"\n=== {j} ===")
    for r in [r for r in rows if r['judge'] == j]:
        print(f"{r['product_id']} {r['product_name'][:28]}（{r['category']} {r['price']}円 売{r['sales_count']}）強[{r['strong']}] 中[{r['medium']}] 無難[{r['negative']}]")
