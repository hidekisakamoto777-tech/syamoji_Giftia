// app/TagPicker.tsx — 贈る相手のタイプ（タグ）を選ぶ欄（Issue #14、要件 FR-04-02）
// シーンで「誕生日」を選んだときだけ、page.tsx から表示される。
// タグは画面に固定値で持つ（タグ一覧の API は作らない）。ID と名前は DB の tag_id テーブルと同じ
// （backend/sql/001_create_tag_tables.sql）。

// 選べるタグの数の上限（API 側の MAX_TAGS と同じ。要件定義書 4.2・4.3）
export const MAX_TAGS = 2;

// 5種類のタグ（id は API に送る値、name は画面に出す名前）
export const TAGS = [
  { id: "T0001", name: "ちょっと変わったものが好き" },
  { id: "T0002", name: "おしゃれな物や部屋づくりにこだわる" },
  { id: "T0003", name: "味や品質を探求するのが好き" },
  { id: "T0004", name: "家でくつろぐ時間が好き" },
  { id: "T0005", name: "定番で安心なものがいい" },
];

type Props = {
  value: string[];                     // 今選んでいるタグの id
  onChange: (next: string[]) => void;  // 選び直したら、親（page.tsx）に知らせる
};

export default function TagPicker({ value, onChange }: Props) {
  const isFull = value.length >= MAX_TAGS; // もう2個選んでいるか

  // 押したタグを、選んでいれば外し、選んでいなければ足す
  const toggle = (id: string) => {
    if (value.includes(id)) onChange(value.filter((v) => v !== id));
    else if (!isFull) onChange([...value, id]);
  };

  return (
    <div className="tag-picker">
      <span className="tag-label">贈る相手のタイプ（{MAX_TAGS}個まで）</span>
      <div className="tag-list">
        {TAGS.map((t) => {
          const selected = value.includes(t.id);
          return (
            // aria-pressed：読み上げソフトに「押されている／いない」を伝える属性
            // 2個選んだら、選んでいないタグは押せなくする（3個目は選べない）
            <button
              key={t.id}
              type="button"
              className={selected ? "tag-btn on" : "tag-btn"}
              aria-pressed={selected}
              disabled={!selected && isFull}
              onClick={() => toggle(t.id)}
            >
              {t.name}
            </button>
          );
        })}
      </div>
      {isFull && <span className="tag-hint">タグは{MAX_TAGS}個まで選べます。変えるときは、選んだタグをもう一度押して外してください。</span>}
    </div>
  );
}
