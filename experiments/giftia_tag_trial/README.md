# Bさん向けタグ付けの試作

班で手法を相談するための試作です。要求・要件は未合意で、ここにある定義やルールは決定事項ではありません。

## 中身

| 場所 | 内容 |
| --- | --- |
| `data/products_paste.txt` | Workbench からコピーした products（2,000件：G0001〜G1000、G7001〜G8000） |
| `data/products.json` | 上を読み込みやすい形に変換したもの |
| `data/products_all_paste.txt` | 全8,000件（G0001〜G8000）。SQLの JSON_ARRAYAGG で1マスにまとめてコピーしたもの |
| `data/products_all.json` | 上を商品ID順に並べた JSON（`scripts/parse_json_cell.py` で作成）。これからはこれを使う |
| `data/products_G1001-G2000_paste.txt` | 追加でコピーした products（1,000件：G1001〜G2000。ID・商品名・カテゴリー・説明文の4列） |
| `data/products_G1001-G2000.json` | 上を変換したもの（`scripts/parse_quoted.py` で作成） |
| `out/sentence_list.xlsx` | 言い回しを決めるための一覧。正解データ用200件の取り分け／残り7,800件の文の種類（900）／取り除いた決まり文句（341）。中の「使い方」シートを先に読む |
| `out/tag_definitions.md` | タグ5つの定義文（案） |
| `out/tag4_result.csv` | 4タグ＋定番・安心のルール判定結果。確認列は空欄（班で〇×を付ける） |
| `out/playful_tag_result.csv` | 「ちょっと変わったものが好き」1タグだけで試した最初の結果 |
| `scripts/parse_full.py` | 貼り付けデータ → products.json |
| `scripts/make_sentence_list.py` | 上の `out/sentence_list.xlsx` を作る（200件は乱数の種を固定して選ぶので、作り直しても同じ200件） |
| `scripts/parse_json_cell.py` | 1マスにまとめたJSONの貼り付けデータ → 商品ID順の JSON（取り出し用のSQLもここに書いてある） |
| `scripts/parse_quoted.py` | 4列（'ID','商品名','カテゴリー','説明文'）の貼り付けデータ → JSON |
| `scripts/tag_rule_clean.py` | 説明文から定型文を消す処理 |
| `scripts/tag_rules4.py` | 4タグ＋定番・安心のルール判定（言い回しの一覧もここ） |
| `scripts/tag_rule.py` | 1タグ版の判定（最初の試作） |

## 動かし方

このフォルダで実行します。Python 3 だけで動きます（追加のインストールは不要）。

```bash
python3 scripts/parse_full.py data/products_paste.txt data/products.json
```

```bash
python3 scripts/tag_rules4.py data/products.json out
```

言い回しを決めるための一覧（Excel）を作るときは、次を実行します。`out/sentence_list.xlsx` が上書きされるので、書き込んだあとのファイルは別の名前で保存してください。

```bash
python3 scripts/make_sentence_list.py data/products_all.json out/sentence_list.xlsx
```

2つ目を実行すると、`out/tag4_result.csv` が上書きされます。〇×を付けたあとのCSVは、別の名前で保存してから実行してください。

## 判定のしくみ

1. 商品名と、定型文（のし・配送・年代やシーンなど）を消した説明文をつなげる
2. タグごとの言い回しの一覧（確実・弱い・除外）が、文章にそのまま含まれるかを調べる
3. 確実に当たり除外に当たらない → 自動、弱いだけ・除外にも当たる → 要確認、どれもなし → なし

e5（意味の近さ）はまだ使っていません。
