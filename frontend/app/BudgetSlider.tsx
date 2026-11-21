// app/BudgetSlider.tsx — 予算の下限・上限を選ぶスライダー（Issue #16、要件 FR-08-01）
// 1本のバーに「下限」「上限」の2つのつまみを付ける。0〜15,000円を500円単位で選ぶ。
// 「下限なし」「上限なし」にチェックしている間は、その側のつまみを灰色にして動かせなくする。

// スライダーで選べる範囲と、1目盛りの幅（円）
export const BUDGET_MIN = 0;
export const BUDGET_MAX = 15000;
export const BUDGET_STEP = 500;

// 予算欄の状態（画面が覚えておく値）
export type Budget = {
  min: number;      // 下限のつまみの位置（円）
  max: number;      // 上限のつまみの位置（円）
  noMin: boolean;   // 「下限なし」にチェックしているか
  noMax: boolean;   // 「上限なし」にチェックしているか
};

// 画面を開いたときの値：3,000円〜5,000円
export const INITIAL_BUDGET: Budget = { min: 3000, max: 5000, noMin: false, noMax: false };

// 予算欄の状態から、API に送る下限・上限を作る。「なし」の側は null（＝送らない）
export function budgetToPrices(b: Budget): { priceMin: number | null; priceMax: number | null } {
  return {
    priceMin: b.noMin ? null : b.min,
    priceMax: b.noMax ? null : b.max,
  };
}

// 金額を「3,000円」の形にする
const yen = (n: number) => `${n.toLocaleString("ja-JP")}円`;

type Props = {
  value: Budget;                     // 今の状態
  onChange: (next: Budget) => void;  // 状態が変わったら、親（page.tsx）に知らせる
};

export default function BudgetSlider({ value, onChange }: Props) {
  const { min, max, noMin, noMax } = value;

  // つまみ同士が追い越さないようにする（下限 ≦ 上限）
  const changeMin = (v: number) => onChange({ ...value, min: Math.min(v, max) });
  const changeMax = (v: number) => onChange({ ...value, max: Math.max(v, min) });

  // チェックを入れたら、つまみを端（0円／15,000円）に戻す
  const toggleNoMin = (checked: boolean) => onChange({ ...value, noMin: checked, min: checked ? BUDGET_MIN : min });
  const toggleNoMax = (checked: boolean) => onChange({ ...value, noMax: checked, max: checked ? BUDGET_MAX : max });

  // 2つのつまみが重なったとき、どちらを上に置くか。
  // 下限のつまみが右半分にあるときは下限を上に置く（右端で重なっても、下限を左へ動かせるように）
  const minOnTop = min > BUDGET_MAX / 2;

  // バーの色を塗る範囲（％）
  const left = ((min - BUDGET_MIN) / (BUDGET_MAX - BUDGET_MIN)) * 100;
  const right = ((max - BUDGET_MIN) / (BUDGET_MAX - BUDGET_MIN)) * 100;

  return (
    // 2行×5列の表の形（グリッド）
    // 1行目：予算｜下限の枠｜〜｜上限の枠｜スライダー
    // 2行目：（空き）｜下限なし｜（空き）｜上限なし｜（空き）
    <div className="budget">
      <span className="budget-label">予算</span>
      {/* 選んだ金額を見せる枠。キーワード欄と同じ高さにするため input を使う（読み取り専用。金額はスライダーで選ぶ） */}
      <input className="budget-box" readOnly tabIndex={-1} aria-label="選んだ予算の下限" value={noMin ? "下限なし" : `下限 ${yen(min)}`} />
      <span>〜</span>
      <input className="budget-box" readOnly tabIndex={-1} aria-label="選んだ予算の上限" value={noMax ? "上限なし" : `上限 ${yen(max)}`} />

      <div className="budget-range">
        <div className="budget-track" />
        <div className="budget-fill" style={{ left: `${left}%`, width: `${right - left}%` }} />
        <input
          type="range"
          aria-label="予算の下限"
          min={BUDGET_MIN} max={BUDGET_MAX} step={BUDGET_STEP}
          value={min}
          disabled={noMin}
          onChange={(e) => changeMin(Number(e.target.value))}
          style={{ zIndex: minOnTop ? 2 : 1 }}
        />
        <input
          type="range"
          aria-label="予算の上限"
          min={BUDGET_MIN} max={BUDGET_MAX} step={BUDGET_STEP}
          value={max}
          disabled={noMax}
          onChange={(e) => changeMax(Number(e.target.value))}
          style={{ zIndex: minOnTop ? 1 : 2 }}
        />
      </div>

      <span />{/* 「予算」の下は空き */}
      <label className="chk"><input type="checkbox" checked={noMin} onChange={(e) => toggleNoMin(e.target.checked)} /> 下限なし</label>
      <span />{/* 「〜」の下は空き */}
      <label className="chk"><input type="checkbox" checked={noMax} onChange={(e) => toggleNoMax(e.target.checked)} /> 上限なし</label>
    </div>
  );
}
