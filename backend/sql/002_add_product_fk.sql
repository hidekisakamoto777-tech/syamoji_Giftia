-- Issue #（番号を記入）：product_favorite に、商品表（products）への外部キーを追加する
-- 対応：BR-01 → FR-03-01（要件定義書 5.2：product_favorite.product_id は「products に存在するID」）
--
-- 【何をするか】
--   product_favorite.product_id に、「products.product_id にある値しか入れられない」という決まり（外部キー）を足す。
--   データは消えない。行も、テーブルも、変えない（決まりを1つ足すだけ）。
--
-- 【現状の記録】2026-11-23 に班のDB（giftia_t602）を確認したところ、この外部キーは「すでに付いていた」。
--   ・information_schema.KEY_COLUMN_USAGE で、product_favorite.product_id → products.product_id
--     （fk_product_favorite_product）を確認した。
--   ・確認後の product_favorite の行数：2,792行（変化なし）
--   ・班のDBでは、もう流す必要はない。もう一度流すと、エラー1826（同じ名前の外部キーがある）になる。害はない。
--   ・このファイルは、新しいDBを作り直すときのための記録として残す。
--
-- 【流す前に】共有DB（班のDB：giftia_t602）のスキーマ変更です。
--   ・班に連絡して、了承をもらってから流す（AGENTS.md 5章）
--   ・流すのは、1回だけ。2回流すと「すでに存在する」エラーになる（害はない）
--   ・消す操作（DELETE・DROP TABLE）は、含まない。ON DELETE は RESTRICT（子の行がある商品は、消せない）
--
-- 【確認済み（流す前に、読むだけのSQLで確認した結果）】実施日：（実行した日を記入）
--   1. products.product_id は、主キー（SHOW INDEX FROM products; → Key_name＝PRIMARY、Column_name＝product_id）
--   2. 2つの product_id は、同じ型・文字コード（varchar(10)、utf8mb4、utf8mb4_ja_0900_as_cs）
--   3. 商品表にない商品IDの行は、0件
--   4. 流す前の product_favorite の行数：2,792行
--
-- 【流し方】MySQL Workbench で、先に `USE giftia_t602;` を実行してから、下の ALTER TABLE を1回だけ流す。

ALTER TABLE product_favorite
  ADD CONSTRAINT fk_product_favorite_product
  FOREIGN KEY (product_id) REFERENCES products (product_id)
  ON DELETE RESTRICT
  ON UPDATE RESTRICT;

-- 【流したあとの確認】2行（tag_id と product_id）が出ること。行数が、流す前と同じこと（2,792行）
-- SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
-- FROM information_schema.KEY_COLUMN_USAGE
-- WHERE TABLE_SCHEMA = 'giftia_t602' AND TABLE_NAME = 'product_favorite' AND REFERENCED_TABLE_NAME IS NOT NULL;
-- SELECT COUNT(*) AS 行数 FROM product_favorite;

-- 【戻し方】外部キーの決まりを外すだけ（データは、そのまま）
-- ALTER TABLE product_favorite DROP FOREIGN KEY fk_product_favorite_product;
