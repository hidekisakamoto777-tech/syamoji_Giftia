# test_search.py — /api/search のテスト（#13。DBにはつながない）
#
# DB の代わりに「偽の fetch_all」を使い、
#   ・SQL に何が入るか／値がどの順で渡るか
#   ・入力の検証（tag_ids）
#   ・画面に返す形（to_gift）
# を確かめる。実際のDBでの確認は、PR の「確認方法と結果」に書いた手順で別に行う。
#
# 実行（backend/ で）：python -m unittest discover -s tests -v

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402

import main  # noqa: E402

TAGS = [{"tagid": f"T000{i}"} for i in range(1, 6)]


def fake_db(calls, rows=None):
    """fetch_all の代わり。呼ばれた SQL と値を calls に記録し、それらしい結果を返す"""

    def _fetch(query, params=()):
        calls.append((query, params))
        if "FROM tag_id" in query and "JOIN" not in query:
            return TAGS
        if "COUNT(*)" in query:
            return [{"n": len(rows or [])}]
        return rows or []

    return _fetch


def call_search(calls, rows=None, **kw):
    """search() を、画面から呼ばれたときと同じ形（省略した条件は既定値）で呼ぶ"""
    args = dict(q="", category="", indiv_wrap=False, scene="", tag_ids=[], price_min=None, price_max=None, limit=20)
    args.update(kw)
    with patch.object(main, "fetch_all", fake_db(calls, rows)):
        return main.search(**args)


def sql_of(calls, keyword):
    """記録した SQL のうち、keyword を含む最初のもの（SQL, 値）"""
    return next(c for c in calls if keyword in c[0])


ROW = {
    "product_id": "G0001", "category": "お菓子", "brand": "A店", "product_name": "クッキー", "price": 3000,
    "rating": None, "review_count": 0, "description": "説明文", "tag_names": None,
}


class SearchQueryTest(unittest.TestCase):
    def test_タグなし_評価順で_販売数は使わない(self):  # 6.4 No.6
        calls = []
        call_search(calls, price_min=3000, price_max=5000)
        sql, params = sql_of(calls, "LIMIT")
        self.assertIn("ORDER BY p.rating DESC, p.review_count DESC", sql)
        self.assertNotIn("sales_count", sql)
        self.assertNotIn("product_favorite", sql)
        self.assertEqual(params, (3000, 5000, 20))

    def test_在庫0は出さない(self):  # 6.4 No.7
        calls = []
        call_search(calls)
        self.assertIn("p.stock > 0", sql_of(calls, "LIMIT")[0])

    def test_価格はちょうどの値も含む(self):  # 6.4 No.9
        calls = []
        call_search(calls, price_min=3000, price_max=5500)
        sql, _ = sql_of(calls, "LIMIT")
        self.assertIn("p.price >= %s", sql)
        self.assertIn("p.price <= %s", sql)

    def test_シーンを渡すと絞り_渡さないと絞らない(self):
        with_scene, without = [], []
        call_search(with_scene, scene="誕生日")
        call_search(without)
        sql, params = sql_of(with_scene, "LIMIT")
        self.assertIn("product_scenes", sql)
        self.assertEqual(params, ("誕生日", 20))
        self.assertNotIn("product_scenes", sql_of(without, "LIMIT")[0])

    def test_タグを選ぶと類似度の合計順で_選んだタグだけに絞る(self):  # 6.4 No.1・2・3
        calls = []
        call_search(calls, scene="誕生日", tag_ids=["T0002", "T0001"], price_min=3000, price_max=5000)
        sql, params = sql_of(calls, "LIMIT")
        self.assertIn("SUM(f.similarity) AS score", sql)
        self.assertIn("f.tag_id IN (%s, %s)", sql)
        self.assertIn("ORDER BY m.score DESC, p.rating DESC, p.review_count DESC", sql)
        # SQL に出てくる順（タグ → シーン → 価格 → 件数）で値が渡る
        self.assertEqual(params, ("T0002", "T0001", "誕生日", 3000, 5000, 20))

    def test_プレースホルダと値の数が必ず合う(self):
        patterns = [
            {},
            {"q": "送別 お菓子", "category": "お菓子", "indiv_wrap": True, "price_min": 1, "price_max": 2},
            {"tag_ids": ["T0001"], "scene": "誕生日", "q": "茶"},
            {"tag_ids": ["T0001", "T0005"], "indiv_wrap": True, "price_max": 9999},
        ]
        for kw in patterns:
            calls = []
            call_search(calls, **kw)
            for sql, params in [sql_of(calls, "LIMIT"), sql_of(calls, "COUNT(*)")]:
                self.assertEqual(sql.count("%s"), len(params), kw)

    def test_入力の文字はSQLの文章に入らない(self):
        calls = []
        evil = "'; DROP TABLE products; --"
        call_search(calls, q=evil, category=evil, scene=evil)
        for sql, params in calls:
            self.assertNotIn("DROP", sql)
        self.assertIn(evil, sql_of(calls, "LIMIT")[1])


class TagValidationTest(unittest.TestCase):
    def test_3個以上は断る(self):
        with self.assertRaises(HTTPException) as e:
            call_search([], tag_ids=["T0001", "T0002", "T0003"])
        self.assertEqual(e.exception.status_code, 422)

    def test_登録されていないタグは断る(self):
        for bad in (["T9999"], [""], ["T0001", "x"]):
            with self.assertRaises(HTTPException) as e:
                call_search([], tag_ids=bad)
            self.assertEqual(e.exception.status_code, 422)

    def test_断ったときは商品を検索しない(self):
        calls = []
        with self.assertRaises(HTTPException):
            call_search(calls, tag_ids=["T9999"])
        self.assertFalse(any("products" in c[0] for c in calls))

    def test_同じタグが2回来ても1個として扱う(self):
        calls = []
        call_search(calls, tag_ids=["T0001", "T0001"])
        self.assertEqual(sql_of(calls, "LIMIT")[1], ("T0001", 20))

    def test_タグなしのときはタグの表を読まない(self):
        calls = []
        call_search(calls)
        self.assertFalse(any("FROM tag_id" in c[0] for c in calls))

    def test_2個ちょうどは通る(self):
        call_search([], tag_ids=["T0001", "T0002"])


class ResponseTest(unittest.TestCase):
    def test_結果の形_既存の項目は変えず_説明文とタグ名を足す(self):
        row = dict(ROW, rating=4.5, review_count=12, tag_names="おしゃれな物や部屋づくりにこだわる|ちょっと変わったものが好き")
        out = call_search([], rows=[row], tag_ids=["T0001", "T0002"])
        self.assertEqual(out["total"], 1)
        g = out["results"][0]
        self.assertEqual(
            {"id", "category", "brand", "name", "price", "rating", "reviewCount", "description", "matchedTags"}, set(g)
        )
        self.assertEqual(g["id"], "G0001")
        self.assertEqual(g["rating"], 4.5)
        self.assertEqual(g["matchedTags"], ["おしゃれな物や部屋づくりにこだわる", "ちょっと変わったものが好き"])
        self.assertEqual(g["description"], "説明文")

    def test_タグを選ばないときはタグ名が空(self):  # 6.4 No.6「タグ名は出ない」
        g = call_search([], rows=[ROW])["results"][0]
        self.assertEqual(g["matchedTags"], [])

    def test_レビューなしの評価は今までどおり0(self):
        self.assertEqual(call_search([], rows=[ROW])["results"][0]["rating"], 0)

    def test_類似度と根拠は返さない(self):  # 6.4 No.8
        g = call_search([], rows=[dict(ROW, tag_names="x")], tag_ids=["T0001"])["results"][0]
        self.assertNotIn("similarity", g)
        self.assertNotIn("reason", g)
        self.assertNotIn("score", g)


if __name__ == "__main__":
    unittest.main()
