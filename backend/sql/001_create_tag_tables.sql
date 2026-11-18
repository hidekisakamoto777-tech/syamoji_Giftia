-- Issue #8：追加テーブル（tag_id・product_favorite）の作成
-- 対応：BR-01 → FR-03-01、FR-03-02（要件定義書 4.1・5.2・5.3）
--
-- 【流す前に】共有DB（班のAzure MySQL）への変更です。
--   ・接続先が班の開発用DBであること、ほかの3人に知らせたことを確認する
--   ・既存テーブルは変更しません（追加のみ）
--   ・何度流しても同じ状態になります（IF NOT EXISTS、ON DUPLICATE KEY UPDATE）
--   ・戻すとき：下の「戻し方」を使う（このSQLで作った2テーブルだけを消す）
--
-- 【注意】match_text の文言は、2026-11-18時点では「たたき台」（11/16の案B）です。
--   班で文言が決まったら、このファイルの値を直して、もう一度流してください。
--
-- 【確認済み（2026-11-18）】班のDBは giftia_t602。products.product_id は
--   varchar(10)、文字コードは utf8mb4 / utf8mb4_ja_0900_as_cs。下のテーブルも合わせてある。
--   商品への外部キーは、products.product_id が主キーか索引付きであることを確かめてから、
--   最後のコメントを外して追加する。
--
-- 【流し方】MySQL Workbench で、先に `USE giftia_t602;` を実行してから、このファイルを流す。

CREATE TABLE IF NOT EXISTS tag_id (
  tagid      VARCHAR(10)  NOT NULL COMMENT 'タグのID（T0001〜T0005）',
  tag_name   VARCHAR(100) NOT NULL COMMENT 'タグの分類（5種類）',
  definition TEXT         NOT NULL COMMENT 'タグの意味。画面の表示・チーム内の説明用',
  match_text TEXT         NOT NULL COMMENT '類似度の計算に使う説明文。画面には出さない',
  PRIMARY KEY (tagid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_ja_0900_as_cs;

CREATE TABLE IF NOT EXISTS product_favorite (
  product_id VARCHAR(10)  NOT NULL COMMENT '商品ID（productsにある商品）',
  tag_id     VARCHAR(10)  NOT NULL COMMENT 'タグのID（tag_id.tagid）',
  similarity DECIMAL(5,4) NOT NULL COMMENT '説明文とmatch_textの類似度（0〜1）。並び順に使う',
  writer     VARCHAR(10)  NOT NULL COMMENT 'タグを付けたのが自動処理か人か（自動／人）',
  reason     TEXT         NULL     COMMENT '根拠の一文。画面には出さない',
  checked_by VARCHAR(50)  NULL     COMMENT '確認した商品部の担当者。未確認ならNULL',
  tagged_at  DATE         NOT NULL COMMENT 'タグを登録した日付',
  PRIMARY KEY (product_id, tag_id),
  -- 検索は「選んだタグが付いた商品」を探すので、tag_id だけで引ける索引を付ける
  KEY idx_product_favorite_tag_id (tag_id),
  CONSTRAINT fk_product_favorite_tag FOREIGN KEY (tag_id) REFERENCES tag_id (tagid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_ja_0900_as_cs;

-- タグ5件（要件定義書 5.2「タグの一覧」と「計算用の説明文」）
INSERT INTO tag_id (tagid, tag_name, definition, match_text) VALUES
('T0001', 'ちょっと変わったものが好き',
 '人とは少し違う個性的なものや、意外性・珍しさのあるものに魅力を感じる。ありきたりなものよりも、ユニークさや話題性、遊び心のある商品を好む。',
 '見た目や形にユーモアがある、ほかではあまり見かけない珍しい雑貨や食べもの。思わず笑ったり、人に話したくなったりする、遊び心のある意外な品。'),
('T0002', 'おしゃれな物や部屋づくりにこだわる',
 'デザインや色合い、素材感、見た目の美しさを重視する。インテリアや身の回りのアイテムに統一感やセンスを求め、空間全体をおしゃれに演出できるものを好む。',
 'デザインや色合い、素材感が美しく、部屋に飾ったり置いたりすると空間がおしゃれになる商品。作家ものの器やガラス、アートや照明など、見た目のセンスにこだわったインテリア雑貨。'),
('T0003', '味や品質を探求するのが好き',
 '食べ物や飲み物の味わい、素材、製法、品質にこだわりがある。定番の商品だけでなく、上質なものや専門性の高いもの、新しい味わいとの出会いを楽しむ。',
 '素材や産地、製法にこだわった、上質な食べ物や飲み物。味わいの違いを飲み比べ・食べ比べして楽しめる、専門店ならではの本格的な品。'),
('T0004', '家でくつろぐ時間が好き',
 '自宅でリラックスして過ごす時間を大切にする。快適さや心地よさを重視し、日常のくつろぎ時間をより豊かにしてくれる商品やアイテムを好む。',
 '自宅でリラックスして過ごす時間を心地よくする商品。お風呂や寝る前、休日にゆったりくつろげる、入浴剤や香り、肌ざわりのよいアイテム。'),
('T0005', '定番で安心なものがいい',
 '奇抜さや目新しさよりも、実績や信頼性、使いやすさを重視する。多くの人に支持されている定番商品や、品質・機能が安定していて安心して選べるものを好む。',
 '多くの人に長く選ばれている、品質が安定した定番の商品。クセが少なく好みを選ばず、誰にでも使いやすい、安心して贈れる品。')
ON DUPLICATE KEY UPDATE
  tag_name   = VALUES(tag_name),
  definition = VALUES(definition),
  match_text = VALUES(match_text);

-- 確認：5件が返ること
-- SELECT * FROM tag_id;

-- 商品への外部キー（products.product_id の型・文字コードを確認してから実行する）
-- ALTER TABLE product_favorite
--   ADD CONSTRAINT fk_product_favorite_product FOREIGN KEY (product_id) REFERENCES products (product_id);

-- 戻し方（このSQLで作った2テーブルだけを消す。product_favorite を先に消す）
-- DROP TABLE IF EXISTS product_favorite;
-- DROP TABLE IF EXISTS tag_id;
