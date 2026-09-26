import { useState } from "react";
import { analyzeMolecule } from "../api/client";
import MoleculeInput from "../components/MoleculeInput.jsx";
import ResultCard from "../components/ResultCard.jsx";
import ShapChart from "../components/ShapChart.jsx";
import StructureImage from "../components/StructureImage.jsx";

function Explanation({ data }) {
  if (!data) return null;
  return (
    <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-3 text-sm text-slate-800">
      <p className="m-0">{data.text}</p>
      <p className="mb-0 mt-1 text-xs text-slate-500">
        {data.source === "gemini" ? `Written by ${data.model} from the SHAP output below` : "Template summary (AI explanation unavailable)"}
      </p>
    </div>
  );
}

function PredictionSection({ title, subtitle, result, positiveLabel, tone }) {
  const [selected, setSelected] = useState(result.predictions[0].endpoint);
  const explanation = result.explanations.find((e) => e.endpoint === selected);
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="m-0 text-lg font-semibold text-slate-900">{title}</h2>
      <p className="mb-3 mt-0.5 text-sm text-slate-500">{subtitle}</p>
      <Explanation data={result.plain_english_explanation} />
      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {result.predictions.map((p) => (
          <ResultCard key={p.endpoint} item={p} positiveLabel={positiveLabel} tone={tone}
                      selected={p.endpoint === selected} onSelect={() => setSelected(p.endpoint)} />
        ))}
      </div>
      <div className="mt-4 border-t border-slate-100 pt-3">
        <h3 className="mb-2 mt-0 text-sm font-semibold text-slate-800">
          Why {selected}? <span className="font-normal text-slate-500">(click a card to change)</span>
        </h3>
        <ShapChart contributions={explanation?.contributions} positiveLabel={positiveLabel} />
      </div>
    </section>
  );
}

function DrugLikeness({ data }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="m-0 text-lg font-semibold text-slate-900">Drug-likeness</h2>
      <p className={`mb-2 mt-1 text-sm font-medium ${data.drug_like ? "text-emerald-700" : "text-rose-700"}`}>{data.summary}</p>
      <ul className="m-0 list-none space-y-1 p-0 text-sm">
        {[...data.lipinski.rules, ...data.veber.rules].map((r) => (
          <li key={r.rule} className="flex items-center justify-between gap-2">
            <span className="text-slate-700">{r.rule}</span>
            <span className={`tabular-nums ${r.passed ? "text-emerald-700" : "text-rose-700"}`}>
              {r.value} {r.passed ? "✓" : "✗"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function PredictPage() {
  const [state, setState] = useState({ status: "idle" });

  const analyze = async (smiles) => {
    setState({ status: "loading", smiles });
    try {
      setState({ status: "done", smiles, data: await analyzeMolecule(smiles) });
    } catch (e) {
      setState({ status: "error", smiles, message: e.message });
    }
  };

  const { status, smiles, data, message } = state;
  return (
    <div className="space-y-5">
      <div>
        <h1 className="m-0 text-2xl font-bold text-slate-900">Predict a molecule's properties</h1>
        <p className="mt-1 text-slate-600">
          Bioactivity against six kinases, 13 toxicity endpoints and drug-likeness, each with the features driving the prediction.
        </p>
      </div>
      <MoleculeInput onAnalyze={analyze} loading={status === "loading"} />

      {status === "loading" && (
        <div role="status" className="rounded-xl border border-slate-200 bg-white p-6 text-center text-slate-600">
          Running models and writing the explanation… (a few seconds)
        </div>
      )}
      {status === "error" && (
        <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-800">
          <strong>Could not analyze that molecule.</strong> {message}
        </div>
      )}
      {status === "done" && (
        <div className="grid gap-5 lg:grid-cols-[18rem_minmax(0,1fr)]">
          <div className="space-y-5">
            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <StructureImage smiles={smiles} label="Input molecule" width={400} height={300} />
              <p className="mb-0 mt-2 break-all font-mono text-xs text-slate-500">{smiles}</p>
            </section>
            <DrugLikeness data={data.druglikeness} />
          </div>
          <div className="space-y-5">
            <PredictionSection key={`bio-${smiles}`} title="Bioactivity" result={data.bioactivity}
              subtitle="Probability the molecule inhibits each kinase at IC50 ≤ 1 µM." positiveLabel="active" tone="good" />
            <PredictionSection key={`tox-${smiles}`} title="Toxicity" result={data.toxicity}
              subtitle="Probability of a positive result in 12 Tox21 assays and ClinTox clinical-trial toxicity." positiveLabel="toxic" tone="danger" />
          </div>
        </div>
      )}
      <p className="text-xs text-slate-500">
        Computational predictions from models trained on public data (ChEMBL, Tox21, ClinTox). Not a substitute for lab testing.
      </p>
    </div>
  );
}
