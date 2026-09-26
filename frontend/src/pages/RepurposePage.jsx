import { useEffect, useRef, useState } from "react";
import { repurpose, searchDiseases } from "../api/client";
import StructureImage from "../components/StructureImage.jsx";

const EXAMPLES = ["Chronic myeloid leukemia", "Type 2 diabetes", "Alzheimer's disease", "Breast cancer", "Hypertension"];
const SIGNAL_LABELS = { target: "Shared target", similarity: "Similarity", model: "Bioactivity model" };

function DiseaseSearch({ onSelect, loading }) {
  const [text, setText] = useState("");
  const [options, setOptions] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      searchDiseases(text).then((r) => !cancelled && setOptions(r)).catch(() => !cancelled && setOptions([]));
    }, 200);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [text, open]);

  const choose = (name) => { setText(name); setOpen(false); onSelect(name); };

  return (
    <form onSubmit={(e) => { e.preventDefault(); if (text.trim()) choose(text.trim()); }}
          className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <label htmlFor="disease" className="mb-1 block text-sm font-medium text-slate-700">Disease</label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input id="disease" value={text} autoComplete="off" role="combobox" aria-expanded={open} aria-controls="disease-options"
                 onChange={(e) => { setText(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
                 onBlur={() => setTimeout(() => setOpen(false), 150)}
                 onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
                 placeholder="Search e.g. leukemia, diabetes, hypertension…"
                 className="w-full rounded-lg border border-slate-300 p-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200" />
          {open && options.length > 0 && (
            <ul id="disease-options" role="listbox"
                className="absolute z-10 mt-1 max-h-72 w-full overflow-auto rounded-lg border border-slate-200 bg-white p-0 shadow-lg">
              {options.map((o) => (
                <li key={o.name} role="option" aria-selected="false" onMouseDown={() => choose(o.name)}
                    className="flex cursor-pointer list-none justify-between px-3 py-2 text-sm hover:bg-indigo-50">
                  <span>{o.name}</span><span className="text-xs text-slate-400">{o.n_drugs} approved drugs</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <button type="submit" disabled={loading || !text.trim()}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60">
          {loading ? "Searching…" : "Find candidates"}
        </button>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500">Try:</span>
        {EXAMPLES.map((ex) => (
          <button key={ex} type="button" onClick={() => choose(ex)}
                  className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-700 hover:border-indigo-400 hover:text-indigo-700">
            {ex}
          </button>
        ))}
      </div>
    </form>
  );
}

function CandidateCard({ rank, c }) {
  const known = c.most_similar_known_drug;
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="m-0 text-lg font-semibold text-slate-900">
            <span className="mr-2 text-slate-400">#{rank}</span>{c.drug}
          </h3>
          {c.currently_approved_for.length > 0 && (
            <p className="mb-0 mt-0.5 text-xs text-slate-500">Currently approved for: {c.currently_approved_for.join(", ")}</p>
          )}
        </div>
        <div className="w-40" title="Combined score from the signals below">
          <div className="text-right text-sm font-semibold text-indigo-700">Score {c.score.toFixed(2)}</div>
          <div className="mt-1 h-2 rounded bg-slate-100"><div className="h-2 rounded bg-indigo-500" style={{ width: `${c.score * 100}%` }} /></div>
        </div>
      </div>

      <div className="mt-3 grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <div className="grid grid-cols-2 gap-2">
          <StructureImage smiles={c.smiles} label={c.drug} width={260} height={200} />
          {known ? (
            <StructureImage smiles={known.smiles} label={`${known.name} (Tanimoto ${known.tanimoto.toFixed(2)})`} width={260} height={200} />
          ) : <div />}
        </div>
        <div>
          <h4 className="m-0 text-sm font-semibold text-slate-800">Why this drug?</h4>
          <ul className="mb-2 mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {c.reasons.map((r) => <li key={r}>{r}</li>)}
          </ul>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(c.signals).map(([k, v]) => (
              <span key={k} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                {SIGNAL_LABELS[k] ?? k} {v.toFixed(2)}
              </span>
            ))}
          </div>
        </div>
      </div>
    </article>
  );
}

export default function RepurposePage() {
  const [state, setState] = useState({ status: "idle" });
  const last = useRef("");

  const run = async (disease, n = 10) => {
    last.current = disease;
    setState({ status: "loading" });
    try {
      setState({ status: "done", data: await repurpose(disease, n) });
    } catch (e) {
      setState({ status: "error", message: e.message });
    }
  };

  const { status, data, message } = state;
  return (
    <div className="space-y-5">
      <div>
        <h1 className="m-0 text-2xl font-bold text-slate-900">Find repurposing candidates for a disease</h1>
        <p className="mt-1 text-slate-600">
          Approved drugs that share a target protein with existing treatments, or look structurally similar to them.
        </p>
      </div>
      <DiseaseSearch onSelect={(d) => run(d)} loading={status === "loading"} />

      {status === "loading" && <div role="status" className="rounded-xl border border-slate-200 bg-white p-6 text-center text-slate-600">Searching approved drugs…</div>}
      {status === "error" && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-800">{message}</div>}

      {status === "done" && (
        <>
          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="m-0 text-lg font-semibold text-slate-900">{data.matched_diseases.join(" · ")}</h2>
            <p className="mb-2 mt-1 text-sm text-slate-600">
              {data.known_treatments.length} approved treatments · {data.n_candidates} candidate drugs found
            </p>
            <details className="text-sm text-slate-700">
              <summary className="cursor-pointer font-medium">Known treatments and their main targets</summary>
              <p className="mb-1 mt-2"><strong>Treatments:</strong> {data.known_treatments.join(", ")}</p>
              <p className="m-0"><strong>Targets:</strong> {data.known_treatment_targets.map((t) => `${t.name} (${t.n_known_drugs})`).join(", ") || "none recorded"}</p>
            </details>
          </section>
          {data.candidates.length === 0 ? (
            <p className="text-slate-600">No candidates found: no other approved drug shares a target with this disease's treatments.</p>
          ) : (
            <div className="space-y-4">
              {data.candidates.map((c, i) => <CandidateCard key={c.chembl_id} rank={i + 1} c={c} />)}
            </div>
          )}
          {data.n_candidates > data.candidates.length && (
            <button type="button" onClick={() => run(last.current, 50)}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:border-indigo-400">
              Show more (up to 50)
            </button>
          )}
          <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">{data.disclaimer}</p>
        </>
      )}
    </div>
  );
}
