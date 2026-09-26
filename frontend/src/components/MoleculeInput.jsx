import { Suspense, lazy, useRef, useState } from "react";

const KetcherEditor = lazy(() => import("./KetcherEditor.jsx"));

const EXAMPLES = [
  { name: "Erlotinib", smiles: "COCCOc1cc2ncnc(Nc3cccc(C#C)c3)c2cc1OCCOC" },
  { name: "Imatinib", smiles: "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1" },
  { name: "Bisphenol A", smiles: "CC(C)(c1ccc(O)cc1)c1ccc(O)cc1" },
  { name: "Aspirin", smiles: "CC(=O)Oc1ccccc1C(=O)O" },
  { name: "Caffeine", smiles: "Cn1cnc2c1c(=O)n(C)c(=O)n2C" },
];

export default function MoleculeInput({ onAnalyze, loading }) {
  const [mode, setMode] = useState("paste");
  const [smiles, setSmiles] = useState("");
  const [error, setError] = useState("");
  const ketcherRef = useRef(null);

  const switchMode = async (next) => {
    if (next === mode) return;
    setError("");
    if (mode === "draw" && ketcherRef.current) {
      try { setSmiles(await ketcherRef.current.getSmiles()); } catch { /* empty canvas */ }
    }
    setMode(next);
  };

  const handleReady = (ketcher) => {
    ketcherRef.current = ketcher;
    if (smiles.trim()) ketcher.setMolecule(smiles.trim()).catch(() => {});
  };

  const submit = async (e) => {
    e?.preventDefault();
    setError("");
    let value = smiles.trim();
    if (mode === "draw") {
      try { value = (await ketcherRef.current.getSmiles()).trim(); } catch { value = ""; }
      setSmiles(value);
    }
    if (!value) {
      setError(mode === "draw" ? "Draw a molecule on the canvas first." : "Enter a SMILES string, or pick an example.");
      return;
    }
    onAnalyze(value);
  };

  const pickExample = (s) => {
    setSmiles(s);
    setError("");
    if (mode === "draw" && ketcherRef.current) ketcherRef.current.setMolecule(s).catch(() => {});
  };

  return (
    <form onSubmit={submit} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div role="tablist" className="mb-3 inline-flex rounded-lg bg-slate-100 p-1 text-sm">
        {[["paste", "Paste SMILES"], ["draw", "Draw structure"]].map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={mode === id} onClick={() => switchMode(id)}
                  className={`rounded-md px-3 py-1.5 font-medium transition ${
                    mode === id ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}>
            {label}
          </button>
        ))}
      </div>

      {mode === "paste" ? (
        <>
          <label htmlFor="smiles" className="mb-1 block text-sm font-medium text-slate-700">SMILES string</label>
          <textarea id="smiles" value={smiles} onChange={(e) => setSmiles(e.target.value)} rows={2} spellCheck={false}
                    placeholder="e.g. CC(=O)Oc1ccccc1C(=O)O"
                    className="w-full rounded-lg border border-slate-300 p-2 font-mono text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200" />
        </>
      ) : (
        <Suspense fallback={<div className="flex h-[520px] items-center justify-center text-sm text-slate-500">Loading molecule editor…</div>}>
          <KetcherEditor onReady={handleReady} />
        </Suspense>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500">Examples:</span>
        {EXAMPLES.map((ex) => (
          <button key={ex.name} type="button" onClick={() => pickExample(ex.smiles)}
                  className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-700 hover:border-indigo-400 hover:text-indigo-700">
            {ex.name}
          </button>
        ))}
      </div>

      {error && <p role="alert" className="mt-2 text-sm text-rose-600">{error}</p>}

      <button type="submit" disabled={loading}
              className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
        {loading ? "Analyzing…" : "Analyze molecule"}
      </button>
    </form>
  );
}
