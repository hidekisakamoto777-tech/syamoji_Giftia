# main.py — Giftia 検索API（2週目・完成例）
# 画面（Next.js）から呼ばれる「窓口」。条件を受け取り、班のDBを検索して、結果を JSON で返す。
#
# 起動：uvicorn main:app --reload
# 確認：http://localhost:8000/docs（Swagger UI。ブラウザから API を試せる）

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database import fetch_all, get_connection

load_dotenv()  # .env を読む（DB の接続情報・CORS の許可）

app = FastAPI(title="Giftia Search API（2週目）")

# ── CORS ───────────────────────────────────────
# 画面（http://localhost:3000）と API（http://localhost:8000）は別のアプリ＝オリジンが違う。
# ブラウザは既定で「別オリジンへの通信」を止めるので、API 側が「この画面からは受け付ける」と宣言する。
# 許可する画面の URL は .env の CORS_ORIGINS に書く（カンマ区切りで複数可）。空なら何も許可しない。
origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["*"])


@app.get("/api/health")
def health():
    """つながっているかの確認。どの DB に何件の商品があるか"""
    row = fetch_all("SELECT DATABASE() AS db, COUNT(*) AS products FROM products")[0]
    return {"status": "ok", "db": row["db"], "products": row["products"]}


MAX_TAGS = 2  # 選べるタグは2個まで（要件定義書 4.3・6.2）


@app.get("/api/search")
def search(
    q: str = Query(default="", description="キーワード（空白区切りで複数。すべてを含む商品）"),
    category: str = Query(default="", description="カテゴリー（空ならすべて）"),
    indiv_wrap: bool = Query(default=False, description="true なら、説明文に「個包装」とある商品だけ"),
    scene: str = Query(default="", max_length=50, description="シーン（例：誕生日）。空ならシーンでは絞らない"),
    tag_ids: list[str] = Query(default=[], description="タグID（T0001など）。0〜2個。いずれかが付いた商品に絞る"),
    price_min: int | None = Query(default=None, ge=0, description="価格の下限（以上）"),
    price_max: int | None = Query(default=None, ge=0, description="価格の上限（以下）"),
    limit: int = Query(default=20, ge=1, le=100, description="返す件数"),
):
    """条件に合う商品を、上位 limit 件返す。
    並び順（要件定義書 6.2）：タグを選んだとき＝選んだタグの類似度の合計が高い順。
    同点・タグなしのとき＝評価（rating）の高い順 → レビュー件数の多い順。販売数は使わない"""
    # ① 入力の形を確かめる（DB にはつながない）。同じタグが2回来ても1個として数える
    tag_ids = list(dict.fromkeys(tag_ids))
    if len(tag_ids) > MAX_TAGS:
        raise HTTPException(status_code=422, detail=f"tag_ids は{MAX_TAGS}個までです")

    # ② SQL を組み立てる（値は %s で渡し、SQL の文字列に直接つなげない）
    select_sql, from_sql, from_params, where_sql, where_params, order_sql = build_search_query(
        q, category, indiv_wrap, scene, tag_ids, price_min, price_max
    )

    # ③ DB につなぐのは、検索1回につき1回だけ（F-3）。タグの検証・件数・一覧の3つの質問で、同じ接続を使い回す。
    #    途中でエラーになっても、finally で必ず閉じる
    conn = get_connection()
    try:
        if tag_ids:  # 登録されているタグか（画面だけに頼らず、サーバーでも確かめる）
            known = {r["tagid"] for r in fetch_all("SELECT tagid FROM tag_id", conn=conn)}
            if any(t not in known for t in tag_ids):
                raise HTTPException(status_code=422, detail="tag_ids に、登録されていないタグがあります")
        total = fetch_all(
            f"SELECT COUNT(*) AS n FROM {from_sql} WHERE {where_sql}", (*from_params, *where_params), conn=conn
        )[0]["n"]
        rows = fetch_all(
            f"SELECT {select_sql} FROM {from_sql} WHERE {where_sql} ORDER BY {order_sql} LIMIT %s",
            (*from_params, *where_params, limit),
            conn=conn,
        )
    finally:
        conn.close()
    # ④ DB の行を、画面の Gift 型に詰め替えて返す
    return {"total": total, "results": [to_gift(r) for r in rows]}


def build_search_query(q, category, indiv_wrap, scene, tag_ids, price_min, price_max):
    """検索の SQL の部品を作る。（DB につながなくてもテストできるよう、別の関数にしてある）
    戻り値：SELECT の列、FROM、FROM 側の値、WHERE、WHERE 側の値、ORDER BY"""
    select_sql = "p.product_id, p.category, p.brand, p.product_name, p.price, p.rating, p.review_count, p.description"
    from_sql, from_params = "products p", []

    if tag_ids:
        # 選んだタグが付いた商品ごとに、類似度を足し合わせ、一致したタグ名を集める。
        # 2つ選んで両方付いている商品は、2つ足されるので、自然に上に来る
        marks = ", ".join(["%s"] * len(tag_ids))
        from_sql += f""" JOIN (
              SELECT f.product_id, SUM(f.similarity) AS score,
                     GROUP_CONCAT(t.tag_name ORDER BY f.similarity DESC SEPARATOR '|') AS tag_names
              FROM product_favorite f JOIN tag_id t ON t.tagid = f.tag_id
              WHERE f.tag_id IN ({marks})
              GROUP BY f.product_id
            ) m ON m.product_id = p.product_id"""
        from_params += tag_ids
        select_sql += ", m.tag_names"
        order_sql = "m.score DESC, p.rating DESC, p.review_count DESC, p.product_id"
    else:
        order_sql = "p.rating DESC, p.review_count DESC, p.product_id"  # レビューなし（NULL）は最後

    where, params = ["p.stock > 0"], []  # 在庫切れは出さない
    if scene:
        where.append("EXISTS (SELECT 1 FROM product_scenes s WHERE s.product_id = p.product_id AND s.scene_tag = %s)")
        params.append(scene)
    for word in q.split():  # 「送別 お菓子」→ ["送別", "お菓子"]。語ごとに AND
        where.append("(p.product_name LIKE %s OR p.brand LIKE %s OR p.description LIKE %s)")
        params += [f"%{word}%"] * 3
    if category:
        where.append("p.category = %s")
        params.append(category)
    if indiv_wrap:
        where.append("p.description LIKE %s")  # 「個包装」は列がないので、説明文に書いてあるかで見る
        params.append("%個包装%")
    if price_min is not None:
        where.append("p.price >= %s")
        params.append(price_min)
    if price_max is not None:
        where.append("p.price <= %s")
        params.append(price_max)
    return select_sql, from_sql, from_params, " AND ".join(where), params, order_sql


def to_gift(r: dict) -> dict:
    """DB の列名 → 画面（lib/api.ts の Gift 型）の項目名。画面側は1週目のまま変えない。
    description と matchedTags は今回足した項目（画面の表示は #14・#15 で行う）"""
    tag_names = r.get("tag_names")
    return {
        "id": r["product_id"],
        "category": r["category"],
        "brand": r["brand"],
        "name": r["product_name"],
        "price": r["price"],
        # レビューなしは null（0 にしない）。「レビューなし」と「星0」を区別するため（F-4）。
        # 評価は DB の保存値をそのまま返す。バックエンドで平均を計算し直さない（D-1）
        "rating": float(r["rating"]) if r["rating"] is not None else None,
        "reviewCount": r["review_count"],
        "description": r["description"],
        "matchedTags": tag_names.split("|") if tag_names else [],  # 選んだタグのうち、この商品に付いているもの
    }
