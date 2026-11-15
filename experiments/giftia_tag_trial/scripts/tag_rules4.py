# 4タグ＋定番・安心のルール判定（試作）
import sys, json, csv, collections
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tag_rule_clean import clean

P = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = sys.argv[2]

# strong に当たれば自動、medium だけなら要確認、exclude に当たれば要確認に下げる
RULES = {
    'playful': {
        'label': 'ちょっと変わったものが好き',
        'strong': ['箱を開けたときの驚き', 'ほかではあまり見かけない', 'ふざけた文面', '思わず笑って', '思わず二度見',
                   '話しかけたくなる', '話のたね', 'ちょっと意外な贈りもの', 'SNSで話題', '会話が生まれる', 'とぼけた表情',
                   '食品サンプルのよう', 'そっくりの形', '生きもののような形', '机の上がにぎやか', 'ふしぎな手ざわり',
                   '通好み', '表情の違う動物'],
        'medium': ['遊び心', '珍味', '世界にひとつ', '表情は一つひとつ'],
        'exclude': [],
    },
    'stylish': {
        'label': 'おしゃれな物や部屋づくりにこだわる',
        'strong': ['作家のサイン', '作家もの', '版画', '部屋の雰囲気が変わる', '置いておきたくなる形', 'デザイナーが一つずつ',
                   '置物になる', '吹きガラス', '色の重なりが美しい', 'インテリアにもなる', '洗面台が華やぐ', '昔の家電を思わせる',
                   'レトロデザイン', 'アートポスター', 'アートプリント'],
        'medium': ['気分が上がる', '形や色に個体差', '工房の窯', '窯元', '絵付け', '手刺繍', '色のきれいな',
                   '真鍮', 'ハーバリウム', '北欧', '光を受けると', 'ガラス作家'],
        'exclude': ['在宅勤務', '消費電力', '電気代'],
    },
    'connoisseur': {
        'label': '味や品質を探求するのが好き',
        'strong': ['飲み比べ', '食べ比べ', '産地の個性', '産地ごと', '産地による', '個性の強い', '個性がしっかり',
                   'テイスティングノート', 'シングルオリジン', 'スタイルの違う', '造り分け', '精米歩合の違う', '農園指定',
                   '茶園を指定', '品種ごとの味の違い', '花によって味の違う', 'クセのある味わい', 'ソムリエ', 'ビーントゥバー',
                   'カカオ分の違い'],
        'medium': ['少量ずつ仕込', '限定醸造', '限定の仕込み', '焙煎したて', '焙煎日', '杜氏', '蒸溜所の歴史', 'ヴィンテージ',
                   '木桶仕込み', '収穫年', '等級と収穫時期', 'ワインの特徴', '豆の産地と味の特徴', '産地と茶園'],
        'exclude': ['入口にぴったり', 'ことばを印刷', 'メッセージを添えた'],
    },
    'relax': {
        'label': '家でくつろぐ時間が好き',
        'strong': ['バスタイム', '入浴剤', 'バスソルト', 'バスボム', 'キャンドル', 'ディフューザー', 'アイマスク',
                   'ゆったりした時間', '香りに包まれる', 'くつろ', 'リラックス', 'おやすみ', '寝る前', 'がんばった日の夜',
                   '体の芯まで温まる'],
        'medium': ['香りを楽しむ', '香りも楽しめる', '調香師', 'ハーブティー', 'カフェインを含まない', 'アロマ', 'じんわり', 'ひと息', 'お風呂'],
        'exclude': ['入浴剤として使え'],
    },
    'classic': {
        'label': '定番で安心なものがいい',
        'strong': ['クセが少なく', '好みを選ばない', '贈る相手を選ばない', '年代を問わず'],
        'medium': ['どなたにも'],
        'exclude': [],
    },
}

def judge(text, rule):
    s = [k for k in rule['strong'] if k in text]
    m = [k for k in rule['medium'] if k in text]
    x = [k for k in rule['exclude'] if k in text]
    if s and not x: return '自動', s + m
    if s or m: return '要確認', s + m + [f'除外:{k}' for k in x]
    return '', []

rows = []
for p in P:
    text = p['product_name'] + ' ' + clean(p['description'])
    r = {**p, 'clean': text}
    for t, rule in RULES.items():
        r[t], r[t + '_hit'] = judge(text, rule)
    # 「変わったもの」と「定番」が両方強く当たるものは要確認に下げる
    if r['playful'] == '自動' and r['classic'] == '自動':
        r['playful'] = '要確認'; r['playful_hit'].append('定番と矛盾')
    rows.append(r)

tags = [t for t in RULES if t != 'classic']
print('タグ別の件数（2,000件）')
for t in RULES:
    a = [r for r in rows if r[t] == '自動']; c = [r for r in rows if r[t] == '要確認']
    s = sorted(r['sales_count'] for r in a)
    print(f"  {RULES[t]['label']}: 自動 {len(a)} / 要確認 {len(c)}  自動の販売数0={sum(r['sales_count']==0 for r in a)} 中央値={s[len(s)//2] if s else '-'}  カテゴリー={collections.Counter(r['category'] for r in a).most_common(3)}")
k = collections.Counter(sum(r[t] == '自動' for t in tags) for r in rows)
print('4タグのうち自動で付いた数ごとの商品数:', dict(sorted(k.items())))
none = [r for r in rows if all(r[t] == '' for t in tags)]
print('4タグのどれにも当たらない商品:', len(none), ' カテゴリー:', collections.Counter(r['category'] for r in none).most_common(5))
pair = collections.Counter()
for r in rows:
    on = [t for t in tags if r[t] == '自動']
    for i in range(len(on)):
        for j in range(i + 1, len(on)): pair[(on[i], on[j])] += 1
print('自動タグの重なり:', dict(pair))

cols = ['product_id', 'product_name', 'category', 'price', 'sales_count', 'review_count']
with open(f'{OUT}/tag4_result.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(cols + sum([[RULES[t]['label'], RULES[t]['label'] + '_根拠', RULES[t]['label'] + '_確認'] for t in RULES], []) + ['clean'])
    for r in rows:
        if any(r[t] for t in RULES):
            w.writerow([r[c] for c in cols] + sum([[r[t], '・'.join(r[t + '_hit']), ''] for t in RULES], []) + [r['clean']])
json.dump([{k: v for k, v in r.items()} for r in rows], open(f'{OUT}/tag4_rows.json', 'w', encoding='utf-8'), ensure_ascii=False)
