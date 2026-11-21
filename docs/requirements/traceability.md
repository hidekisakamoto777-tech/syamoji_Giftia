# 要求・要件・開発の対応表

> 状態：記入中。#11（PR #22）の行から書き始めた。ほかの要求・要件の行はまだありません。行ごとの状態は「状態」の列を見る。

[要求定義書](business_requirements.md)の要求と、[要件定義書](system_requirements.md)の機能・データ・非機能要件を紐づけ、Issue、PR、確認結果まで追えるようにします。

## 対応表

<!-- 班で要求・要件を記入した後に行を追加してください。IDと文書内の該当箇所へのリンクを記載します。 -->

| 要求ID・参照先 | 要件ID・参照先 | 確認方法・テストケース | 仕様の参照先（必要な場合） | Issue | PR | 確認結果・証拠 | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [BR-01](business_requirements.md) | [FR-03-01](system_requirements.md#41-機能一覧)（[3章](system_requirements.md#3-要求要件マッピングwith) FR-03） | 3章 FR-03 の確認方法：[6.4](system_requirements.md#64-良し悪しの確かめ方テストケース)のテストに使う商品で、product_favorite にタグ・類似度・根拠の一文が入っていることをSQLで確かめる（6.4 No.1・2・3・5） | [5.4](system_requirements.md#54-データ供給計画)・[5.5](system_requirements.md#55-タグの付け方手順) | [#11](https://github.com/satosyun-maro/syamoji_Giftia/issues/11) | [#22](https://github.com/satosyun-maro/syamoji_Giftia/pull/22) | 2026-11-21 SQLで確認（上位5%）：product_favorite に2,792行（全部 writer＝自動）。タグ別 T0001 410・T0002 411・T0003 405・T0004 402・T0005 1,164。No.1：誕生日・3,000〜5,000円・在庫ありの商品のうち160件に T0002。No.2：同じ条件で T0001・T0002 の両方が16件（並び順は検索APIで確かめる）。No.3・No.5 は未確認。タグの付き方：タグごとに上位5%から10件（計50件）を4人で評価し、説明文全部を読むとタグの説明と合っていることを確認、問題ないと結論（2026-11-21） | 確認中（PR レビュー中。要件定義書の修正は4人の合意待ち） |
| [BR-07](business_requirements.md) | [FR-03-01](system_requirements.md#41-機能一覧)（[3章](system_requirements.md#3-要求要件マッピングwith) FR-03・04・08） | 3章 BR-07 の確認方法：同じ価格帯の既存の検索と比べ、タグ経由でだけ上位に出てくる商品があることを確かめる | [5.5](system_requirements.md#55-タグの付け方手順) | [#11](https://github.com/satosyun-maro/syamoji_Giftia/issues/11) | [#22](https://github.com/satosyun-maro/syamoji_Giftia/pull/22) | 未確認（タグのデータは入った。検索APIとあわせて確かめる） | 未確認 |
| —（非機能要件のため要求IDなし） | [8章](system_requirements.md#8-非機能要件with) 運用・保守性（要件IDなし） | タグ付けスクリプトをもう一度流せて、writer・checked_by・tagged_at が残ること | [5.5](system_requirements.md#55-タグの付け方手順) | [#11](https://github.com/satosyun-maro/syamoji_Giftia/issues/11) | [#22](https://github.com/satosyun-maro/syamoji_Giftia/pull/22) | 2026-11-21 確認：スクリプトは backend/scripts/tag_products.py。班のDBに4回書き込み（10%で3回、5%で1回）、毎回「自動・未確認」の行が入れ替わった（重ならない）。今は5%の2,792行。writer＝自動・tagged_at＝2026-11-21・checked_by＝NULL。人の行・確認済みの行（checked_by あり）を残すことは、にせもののDBでだけ確かめた | 確認中（PR レビュー中） |

## 記入時の確認

- 要求はBR、機能要件はFR、データ要件はDR、非機能要件はNFRを使用します（例：BR-01、FR-01、FR-01-01）。ここに例の要求・要件を登録したものではありません。
- 1つの要求から複数の要件・Issueへ分かれても構いません。対応関係ごとに行を追加します。
- 要求・要件の本文は定義書に置き、ここではリンクで参照します。要件定義書3章の対応表を別途重複して管理しません。
- 環境整備など直接対応しない作業は、対象外である理由を記載します。
- 状態と確認結果は区別し、未確認のものを完了扱いにしません。

## 更新履歴

| 日付 | 更新箇所・内容 | 更新者 | 関連Issue・PR |
| --- | --- | --- | --- |
| 2026-11-21 | 対応表に、BR-01・BR-07 → FR-03-01 と、8章 運用・保守性の行を追加（タグ付けスクリプト） | じゃけ | [#11](https://github.com/satosyun-maro/syamoji_Giftia/issues/11)・[#22](https://github.com/satosyun-maro/syamoji_Giftia/pull/22) |
