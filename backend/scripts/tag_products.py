# tag_products.py — 商品の説明文とタグの計算用の説明文（match_text）の類似度を計算して、CSV に出す（Issue #11）
#
# 要件定義書 5.4・5.5 のうち、決まっている部分だけを行う。DB には --save-db --write を付けたときだけ書き込む。
#   1. 商品の説明文から、決まり文句（のし・配送・年代など）を取り除く（5.5 の手順B）
#   2. 説明文を文ごとに分け、e5 でベクトル（意味を表す数値の並び）にする
#   3. タグの計算用の説明文（match_text）との類似度を文ごとに出し、いちばん高い文の点数をその商品の点数にする
#      その文を「根拠の一文（reason）」として残す
#   4. 全商品×5タグの点数を CSV に出す。--top-percent を付けると、タグごとに上位◯%を選んだ CSV も出す
#   5. 選ぶときは、班で決めた2つのルールを当てはめる（要件定義書 5.5 の注記）
#      ・カタログギフトは e5 で選ぶ対象から外し、「定番で安心なものがいい」だけを付ける
#      ・逆の意味のタグ（ちょっと変わったもの×定番で安心）が両方付いたら、ならした点数（z）の高い方を残す
#   6. --out-review を付けると、人が確かめる一覧を出す（両方付いて外したもの・選ぶかどうかの境目の商品）
#   7. --save-db を付けると、選んだ結果を product_favorite に入れる準備をする（入れる件数を表示するだけ）
#      --write も付けたときだけ、本当に書き込む。書き込み方：
#      ・前回「自動」で入れた行のうち、まだ誰も確認していない行（checked_by が空）を消してから、今回の結果を入れる
#        （何度流しても、同じ行が重ならない）
#      ・人が入れた行（writer＝人）と、人が確認した行（checked_by が入っている）は消さない
#        同じ商品×タグがあれば、その行を残す（5.5 ④でやり直しても、確認の記録が消えないようにするため）
#      ・途中でエラーになったら、全部取り消す（半分だけ書き込まれた状態にならない）
#
# まだ決まっていないこと（決まったら、ここに足す）
#   ・上位何%で付けるか → 2026-11-21 の打ち合わせで 5% に決定（チームでの評価で見直す）。--top-percent で毎回指定する
#     境目と同じ点数の商品は全部選ぶので、上位◯%より少し多くなることがある
#     （同じ文の商品は同じ点数になる。例：「定番の贈りものです。」は654件が同じ点数。一部だけ選ぶと、商品IDの順で決まってしまう）
#   ・境目の商品を何件ずつ人が見るか → 今は仮に BORDER 件ずつ
#   ・言い回しでの分類を組み合わせるか
#
# 使い方（backend/ で実行する）
#   python scripts/tag_products.py --products ../experiments/giftia_tag_trial/data/products_all.json --out scores.csv
#   python scripts/tag_products.py --from-db --out scores.csv --top-percent 5 --out-selected selected.csv --out-review review.csv
#   --from-db は、.env の接続情報で班の DB の products と tag_id を読む（読むだけ。書き込まない）
#   python scripts/tag_products.py --from-db --out scores.csv --top-percent 5 --out-selected selected.csv --save-db
#   → 入れる件数を確かめる。よければ、最後に --write を足して、もう一度流す（班の DB に書き込む）
#
# 必要な部品：sentence-transformers（e5 を動かす）。requirements.txt に足すのは班の合意のあと。
# 初回はモデル（intfloat/multilingual-e5-small、約470MB）のダウンロードが要る。手元の PC で動き、外部 API は使わない。

import argparse
import csv
import datetime
import json
import os
import re
import sys

import numpy as np

MODEL_NAME = "intfloat/multilingual-e5-small"
SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql", "001_create_tag_tables.sql")

PLAYFUL = "T0001"  # ちょっと変わったものが好き
CLASSIC = "T0005"  # 定番で安心なものがいい（PLAYFUL と逆の意味）
CATALOG = "カタログギフト"  # products の category の値
BORDER = 20  # 境目の商品として、選んだ側・選ばなかった側から何件ずつ出すか（仮の数）

# ---- 1. 決まり文句を取り除く（experiments/giftia_tag_trial/scripts/tag_rule_clean.py の決まりに、手続きの文を足したもの） ----
# 配送・包装・手続きの言葉、年代・シーンの決まり文句を含む文は使わない（「好き」を含む文は残す）
BOILER = ["のし", "納品書", "ラッピング", "メッセージカード", "名入れ", "刻印", "刺繍を承", "まとめてのご注文",
          "会社宛て", "法人様", "20歳", "お届けします", "お届けいたします", "お届け日", "保証書", "かばんに入る",
          "コンパクトな箱", "オフィスでもお渡し", "毎日の暮らしで使って", "日々の生活で活躍", "発送します",
          "お付けします", "お付けできます", "お選びいただけます", "ご指定ください", "ご記入ください", "承ります",
          # カタログギフト・体験ギフトの手続きの文（申し込み方法・URL・期限・予約）。商品がどんな物かは表さない
          "申し込み", "URLが発行", "有効期限", "予約は"]
SCENE = re.compile(r"\d0代|プレゼントに|贈りもの(として|にも)|ギフトにおすすめ|選ばれています|プチギフトにも|ごあいさつ|職場へのちょっとした|喜ばれ")


def split_sentences(description: str) -> list[str]:
    """説明文を文に分け、決まり文句の文を取り除く。1文目は商品そのものの説明なので必ず残す"""
    kept = []
    for i, s in enumerate(re.split(r"[。\n]", description or "")):
        s = s.strip()
        if not s or s.startswith("【"):  # 【保存方法】などの見出し行は使わない
            continue
        if i > 0 and "好き" not in s and (any(b in s for b in BOILER) or SCENE.search(s)):
            continue
        kept.append(s)
    return kept


# ---- 読み込み ----
def use_backend():
    """backend/database.py（.env の接続情報を使う）を読み込めるようにする"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def load_tags_db() -> list[dict]:
    """班の DB の tag_id テーブルから、5つのタグを読む"""
    use_backend()
    from database import fetch_all
    tags = fetch_all("SELECT tagid, tag_name, definition, match_text FROM tag_id ORDER BY tagid")
    if len(tags) != 5:
        raise ValueError(f"tag_id テーブルからタグが5件読めませんでした（{len(tags)}件）")
    return tags


def load_tags(sql_path: str) -> list[dict]:
    """テーブル作成SQL（#8）の INSERT から、5つのタグ（tagid・tag_name・definition・match_text）を読む。
    DB に tag_id テーブルができる前でも、同じ文言で計算できるようにするため"""
    text = open(sql_path, encoding="utf-8").read()
    rows = re.findall(r"\('(T\d{4})',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\)", text)
    if len(rows) != 5:
        raise ValueError(f"{sql_path} からタグが5件読めませんでした（{len(rows)}件）")
    return [{"tagid": r[0], "tag_name": r[1], "definition": r[2], "match_text": r[3]} for r in rows]


def load_products(args) -> list[dict]:
    if args.from_db:
        use_backend()
        from database import fetch_all
        return fetch_all("SELECT product_id, product_name, category, description FROM products ORDER BY product_id")
    return json.load(open(args.products, encoding="utf-8"))


# ---- 2・3. 類似度を計算する ----
def compute_scores(products: list[dict], tags: list[dict]):
    """全商品×タグの点数（類似度）と、根拠の一文を返す"""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    # e5 は、探す側の文の頭に「query: 」、探される側の文の頭に「passage: 」を付けて使う決まり
    tag_vec = model.encode(["query: " + t["match_text"] for t in tags], normalize_embeddings=True)

    sentences = {p["product_id"]: split_sentences(p["description"]) for p in products}
    unique = sorted({s for ss in sentences.values() for s in ss})  # 同じ文は1回だけ計算する（8,000件でも約900種類）
    vecs = model.encode(["passage: " + s for s in unique], normalize_embeddings=True, batch_size=64, show_progress_bar=True)
    sim = dict(zip(unique, vecs @ tag_vec.T))  # 文 → 5タグとの類似度（長さ1のベクトル同士なので、掛け算が類似度になる）

    scores = np.zeros((len(products), len(tags)))
    reasons = [[""] * len(tags) for _ in products]
    for i, p in enumerate(products):
        ss = sentences[p["product_id"]]
        if not ss:  # 説明文がない商品は点数0（タグは付かない）
            continue
        m = np.array([sim[s] for s in ss])
        scores[i] = m.max(axis=0)
        for k, j in enumerate(m.argmax(axis=0)):
            reasons[i][k] = ss[j] + "。"
    return scores, reasons


def zscores(scores):
    """タグごとにならした点数（平均からどれだけ高いか）。タグによって点数の出方が違うので、タグをまたいで比べるときに使う"""
    std = scores.std(axis=0)
    std[std == 0] = 1  # 全部同じ点数のタグ（商品が1件だけ など）で 0 で割らないようにする
    return (scores - scores.mean(axis=0)) / std


# ---- 4. CSV に出す ----
def write_scores(path, products, tags, scores, reasons):
    """全商品×5タグの点数"""
    z = zscores(scores)
    rank = (-scores).argsort(axis=0).argsort(axis=0) + 1  # タグの中での順位（1が最上位）
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig：Excel で開いても文字化けしない
        w = csv.writer(f)
        w.writerow(["product_id", "product_name", "category", "tag_id", "tag_name", "similarity", "z", "rank_in_tag", "reason"])
        for i, p in enumerate(products):
            for k, t in enumerate(tags):
                w.writerow([p["product_id"], p["product_name"], p["category"], t["tagid"], t["tag_name"],
                            f"{scores[i, k]:.4f}", f"{z[i, k]:.3f}", int(rank[i, k]), reasons[i][k]])


# ---- 5. 選ぶ（班で決めたルールを当てはめる） ----
def select(products, tags, scores, top_percent):
    """タグごとに上位 top_percent% を選び、カタログギフトと逆の意味のタグのルールを当てはめる。
    返すもの：選んだ (商品の番号, タグの番号) の集まり、両方付いて外したものの一覧、タグごとの並び順、
              タグごとの選んだ件数（両方付いて外す前）、上位◯%の件数"""
    n = max(1, round(len(products) * top_percent / 100))
    z = zscores(scores)
    is_catalog = [p["category"] == CATALOG for p in products]
    ids = [t["tagid"] for t in tags]
    kp, kc = ids.index(PLAYFUL), ids.index(CLASSIC)

    selected = set()
    orders = []  # タグごとの、選ぶ候補の並び（点数の高い順）。境目の一覧に使う
    cuts = []  # タグごとに、並びの何件目までを選んだか
    for k in range(len(tags)):
        # カタログギフトと、説明文がない商品（点数0）は、e5 で選ぶ候補に入れない
        order = [i for i in np.argsort(-scores[:, k]) if not is_catalog[i] and scores[i, k] > 0]
        cut = min(n, len(order))
        # 境目の商品と同じ点数の商品は、全部選ぶ（同じ点数なのに、一部だけ外れることがないようにする）
        while 0 < cut < len(order) and scores[order[cut], k] == scores[order[cut - 1], k]:
            cut += 1
        orders.append(order)
        cuts.append(cut)
        selected |= {(i, k) for i in order[:cut]}

    # 逆の意味のタグが両方付いたら、ならした点数の高い方を残す（同じなら「定番で安心」を残す）
    removed = []  # (商品の番号, 外したタグの番号, 残したタグの番号)
    for i in range(len(products)):
        if (i, kp) in selected and (i, kc) in selected:
            keep, drop = (kc, kp) if z[i, kc] >= z[i, kp] else (kp, kc)
            selected.discard((i, drop))
            removed.append((i, drop, keep))

    # カタログギフトには「定番で安心なものがいい」だけを付ける
    selected |= {(i, kc) for i in range(len(products)) if is_catalog[i]}
    return selected, removed, orders, cuts, n


FAVORITE_COLUMNS = ["product_id", "tag_id", "similarity", "writer", "reason", "checked_by", "tagged_at"]


def selected_rows(products, tags, scores, reasons, selected):
    """選んだ結果を、product_favorite と同じ列の並びの行にする（タグごと・点数の高い順）"""
    today = datetime.date.today().isoformat()
    rows = []
    for k, t in enumerate(tags):
        for i in sorted((i for i, kk in selected if kk == k), key=lambda i: -scores[i, k]):
            # reason は、説明文のうちタグに一番近い一文（要件定義書5.2）。カタログギフトも同じ
            # checked_by は、人が確かめるまで空（DB では NULL）
            rows.append((products[i]["product_id"], t["tagid"], f"{scores[i, k]:.4f}", "自動", reasons[i][k], None, today))
    return rows


def write_selected(path, rows):
    """選んだ結果を CSV に出す（DB に入れる前に、中身を目で確かめられるようにするため）"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(FAVORITE_COLUMNS)
        w.writerows(rows)  # None（空）は空欄になる


# ---- 7. product_favorite に入れる ----
def save_db(rows, write: bool):
    """前回の「自動」で、まだ確認していない行を消して、今回の行を入れる。
    人の行（writer＝人）と、確認済みの行（checked_by が入っている）は残す。
    write が False のときは、件数を数えて表示するだけ（DB は変えない）"""
    use_backend()
    from database import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT product_id, tag_id, writer, checked_by FROM product_favorite")
            existing = cur.fetchall()
            # 消す行：自動で入れて、まだ誰も確認していない行。それ以外（人の行・確認済みの行）は全部残す
            old_auto = [r for r in existing if r["writer"] == "自動" and r["checked_by"] is None]
            checked = [r for r in existing if r["writer"] == "自動" and r["checked_by"] is not None]
            human = [r for r in existing if r["writer"] == "人"]
            keep = {(r["product_id"], r["tag_id"]) for r in existing} - {(r["product_id"], r["tag_id"]) for r in old_auto}
            new = [r for r in rows if (r[0], r[1]) not in keep]  # 残す行と同じ商品×タグは、残す行の方を使う

            print("product_favorite への書き込み" + ("" if write else "（確認だけ。まだ書き込まない）"))
            print(f"  今ある行：{len(existing)}行（自動・未確認 {len(old_auto)}・自動・確認済み {len(checked)}・人 {len(human)}"
                  f"・その他 {len(existing) - len(old_auto) - len(checked) - len(human)}）")
            print(f"  消す行（前回の自動・未確認）：{len(old_auto)}行")
            print(f"  入れる行（今回の自動）：{len(new)}行（残す行と重なるので入れない：{len(rows) - len(new)}行）")
            print(f"  書き込んだあとの行：{len(existing) - len(old_auto) + len(new)}行")
            if not write:
                print("  よければ、同じ指定に --write を足して、もう一度流してください")
                return

            cur.execute("DELETE FROM product_favorite WHERE writer = %s AND checked_by IS NULL", ("自動",))
            cur.executemany(
                "INSERT INTO product_favorite (product_id, tag_id, similarity, writer, reason, checked_by, tagged_at)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",  # 値は %s で渡す（文字列を SQL に直接つなげない）
                new,
            )
        conn.commit()  # ここまで全部うまくいったときだけ、確定する
        print("  書き込みました")
    except Exception:
        conn.rollback()  # 途中でエラーになったら、消した行も含めて全部元に戻す
        raise
    finally:
        conn.close()


def write_review(path, products, tags, scores, reasons, selected, removed, orders, cuts):
    """人が確かめる一覧。①両方付いて外したもの ②選ぶかどうかの境目の商品（選んだ側・選ばなかった側 BORDER 件ずつ）"""
    z = zscores(scores)
    count = 0
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["kind", "product_id", "product_name", "category", "tag_id", "tag_name",
                    "similarity", "z", "rank_in_tag", "reason", "kept_tag_id"])

        def row(kind, i, k, rank, kept=""):
            p, t = products[i], tags[k]
            w.writerow([kind, p["product_id"], p["product_name"], p["category"], t["tagid"], t["tag_name"],
                        f"{scores[i, k]:.4f}", f"{z[i, k]:.3f}", rank, reasons[i][k], kept])

        for i, drop, keep in removed:
            row("両方付いたので外した", i, drop, orders[drop].index(i) + 1, tags[keep]["tagid"])
            count += 1
        for k, order in enumerate(orders):
            for r in range(max(0, cuts[k] - BORDER), min(len(order), cuts[k] + BORDER)):
                i = order[r]
                row("境目・選んだ" if (i, k) in selected else "境目・選ばなかった", i, k, r + 1)
                count += 1
    return count


def main():
    ap = argparse.ArgumentParser(description="商品とタグの類似度を計算して CSV に出す（DB には書き込まない）")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--products", help="商品の JSON（product_id・product_name・category・description の配列）")
    src.add_argument("--from-db", action="store_true", help="班の DB の products を読む（.env を使う）")
    ap.add_argument("--out", required=True, help="全商品×5タグの点数を出す CSV")
    ap.add_argument("--top-percent", type=float, help="タグごとに上位◯%を選ぶ（例：15）。指定したときだけ --out-selected を出す")
    ap.add_argument("--out-selected", help="選んだ結果を product_favorite の列の並びで出す CSV")
    ap.add_argument("--out-review", help="人が確かめる一覧（両方付いて外したもの・境目の商品）を出す CSV")
    ap.add_argument("--save-db", action="store_true", help="選んだ結果を product_favorite に入れる準備（件数を表示するだけ）")
    ap.add_argument("--write", action="store_true", help="--save-db と一緒に付けると、本当に DB に書き込む")
    args = ap.parse_args()
    if (args.top_percent is None) != (args.out_selected is None):
        ap.error("--top-percent と --out-selected は、両方そろえて指定してください")
    if args.out_review and args.top_percent is None:
        ap.error("--out-review は、--top-percent と --out-selected も指定したときだけ使えます")
    if args.save_db and not (args.from_db and args.top_percent is not None):
        ap.error("--save-db は、--from-db と --top-percent（と --out-selected）も指定したときだけ使えます")
    if args.write and not args.save_db:
        ap.error("--write は、--save-db と一緒に指定してください")
    if args.top_percent is not None and not 0 < args.top_percent <= 100:
        ap.error("--top-percent は 0 より大きく 100 以下にしてください")

    tags = load_tags_db() if args.from_db else load_tags(SQL_PATH)
    ids = [t["tagid"] for t in tags]
    if PLAYFUL not in ids or CLASSIC not in ids:
        raise ValueError(f"タグに {PLAYFUL} と {CLASSIC} が必要です（読めたタグ：{ids}）")
    products = load_products(args)
    print(f"商品 {len(products)}件、タグ {len(tags)}件を読み込みました")
    scores, reasons = compute_scores(products, tags)
    write_scores(args.out, products, tags, scores, reasons)
    print(f"点数を書き出しました：{args.out}（{len(products) * len(tags)}行）")
    if args.top_percent is not None:
        selected, removed, orders, cuts, n = select(products, tags, scores, args.top_percent)
        rows = selected_rows(products, tags, scores, reasons, selected)
        write_selected(args.out_selected, rows)
        print(f"タグごとに上位{args.top_percent:g}%（{n}件。境目と同じ点数の商品も含める）を選びました：{args.out_selected}（{len(selected)}行）")
        for k, t in enumerate(tags):
            extra = f"（同じ点数で {cuts[k] - n}件増えた）" if cuts[k] > n else ""
            print(f"  {t['tagid']} {t['tag_name']}：{sum(1 for _, kk in selected if kk == k)}件{extra}")
        print(f"  逆の意味のタグが両方付いて、片方を外した商品：{len(removed)}件")
        if args.out_review:
            count = write_review(args.out_review, products, tags, scores, reasons, selected, removed, orders, cuts)
            print(f"人が確かめる一覧を書き出しました：{args.out_review}（{count}行）")
        if args.save_db:
            save_db(rows, args.write)


if __name__ == "__main__":
    main()
