// app/page.tsx — Giftia 検索画面（2週目・完成例）
// 1週目との違い：①searchGifts が FastAPI を呼ぶ（async/await）②入力した条件を渡す ③つながらないときの表示
"use client"; // ← ブラウザで動く合図。useState や onClick を使う画面に必要

import { useState } from "react";
import ResultCard from "./ResultCard";
import BudgetSlider, { INITIAL_BUDGET, budgetToPrices, type Budget } from "./BudgetSlider";
import TagPicker from "./TagPicker";
import { searchGifts, type Gift } from "@/lib/api";

// シーンの選択肢（Issue #14）。「誕生日」のときだけタグ欄を出す。
// 「すべてのシーン」はシーンで絞らない（API に scene を送らない）＝これまでどおりの検索
const BIRTHDAY = "誕生日";

export default function Home() {
  // ① 状態（変化するデータ）を覚える箱
  const [mode, setMode] = useState<"standard" | "business">("standard"); // どのタブか
  const [keyword, setKeyword] = useState("");                             // 入力した言葉
  const [category, setCategory] = useState("");                           // 選んだカテゴリー
  const [indivWrap, setIndivWrap] = useState(false);                      // 個包装だけ（取引先へのお礼）
  const [priceBand, setPriceBand] = useState("");                         // 価格帯（取引先へのお礼）
  const [budget, setBudget] = useState<Budget>(INITIAL_BUDGET);           // 予算の下限・上限（いまの検索）
  const [scene, setScene] = useState("");                                 // シーン（"誕生日" か ""＝すべてのシーン）
  const [tagIds, setTagIds] = useState<string[]>([]);                     // 選んだタグ（誕生日のときだけ）
  const [results, setResults] = useState<Gift[] | null>(null);            // 検索結果
  const [error, setError] = useState("");                                 // つながらないときの文言

  // シーンを変えたとき：誕生日から「すべてのシーン」にしたら、選んでいたタグを外す（見えないタグが検索条件に残らないように）
  function onSceneChange(next: string) {
    setScene(next);
    if (next !== BIRTHDAY) setTagIds([]);
  }

  // ② 検索ボタンの処理（API に聞くので、結果が返るまで待つ＝async/await）
  async function onSearch(e: React.FormEvent) {
    e.preventDefault(); // ページの再読み込みを止める
    setError("");
    // いま開いているタブの条件だけを送る（もう一方のタブの入力は送らない）
    // タグは、シーンが誕生日のときだけ送る（念のため、ここでも確かめる）
    const condition = mode === "standard"
      ? { keyword, category, indivWrap: false, priceBand: "", ...budgetToPrices(budget), scene, tagIds: scene === BIRTHDAY ? tagIds : [] }
      : { keyword: "", category: "", indivWrap, priceBand, priceMin: null, priceMax: null, scene: "", tagIds: [] }; // お礼タブは今までどおり
    try {
      setResults(await searchGifts(condition));
    } catch (err) {
      setResults(null);
      setError(`APIにつながりません：${(err as Error).message}`); // 原因はブラウザの Console に出る
    }
  }

  // ③ 画面
  return (
    <main className="page">
      <header className="header"><h1>Giftia</h1></header>

      {/* タブ：state(mode)＋条件で出し分ける */}
      <nav className="modes">
        <button className={mode === "standard" ? "on" : ""} onClick={() => { setMode("standard"); setResults(null); }}>いまの検索</button>
        <button className={mode === "business" ? "on" : ""} onClick={() => { setMode("business"); setResults(null); }}>取引先へのお礼</button>
      </nav>

      <form className={mode === "standard" ? "form form-std" : "form"} onSubmit={onSearch}>
        {mode === "standard" ? (
          <>
            {/* 案B：条件を上の1つの枠に3行でまとめる。1行目＝キーワード・シーン・カテゴリー・検索 */}
            <div className="form-row">
              <input className="q" value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="キーワード（例：送別 お菓子）" />
              <select aria-label="シーン" value={scene} onChange={(e) => onSceneChange(e.target.value)}>
                <option value="">すべてのシーン</option>
                <option value={BIRTHDAY}>誕生日</option>
              </select>
              <select aria-label="カテゴリー" value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="">すべてのカテゴリー</option>
                <option value="コスメ">コスメ</option>
                <option value="食品">食品</option>
                <option value="生活雑貨">生活雑貨</option>
              </select>
              <button type="submit">検索</button>
            </div>
            {/* 2行目：予算の下限・上限（いまの検索だけ） */}
            <BudgetSlider value={budget} onChange={setBudget} />
            {/* 3行目：贈る相手のタイプ（タグ）。シーンが誕生日のときだけ出す（FR-04-02） */}
            {scene === BIRTHDAY && <TagPicker value={tagIds} onChange={setTagIds} />}
          </>
        ) : (
          <>
            <label className="chk"><input type="checkbox" checked={indivWrap} onChange={(e) => setIndivWrap(e.target.checked)} /> 個包装</label>
            <select value={priceBand} onChange={(e) => setPriceBand(e.target.value)}>
              <option value="">すべての価格帯</option>
              <option value="3000">3,000〜5,000円</option>
              <option value="5000">5,000〜10,000円</option>
            </select>
            <button type="submit">検索</button>
          </>
        )}
      </form>

      {error && <p className="summary">{error}</p>}

      {/* 結果：同じ ResultCard を map で並べる（使い回し） */}
      {results && (
        <section>
          <p className="summary">上位 {results.length} 件</p>
          <div className="grid">
            {results.map((g, i) => <ResultCard key={g.id} gift={g} rank={i + 1} />)}
          </div>
        </section>
      )}
    </main>
  );
}
