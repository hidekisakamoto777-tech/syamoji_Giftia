import re
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

