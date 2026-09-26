import { useState } from "react";
import { structureUrl } from "../api/client";

export default function StructureImage({ smiles, label, width = 320, height = 220 }) {
  const [failed, setFailed] = useState(false);
  return (
    <figure className="m-0 flex flex-col items-center">
      <div className="flex w-full items-center justify-center rounded-lg border border-slate-200 bg-white p-2"
           style={{ minHeight: 120 }}>
        {failed ? (
          <span className="text-xs text-slate-400">Structure unavailable</span>
        ) : (
          <img src={structureUrl(smiles, width, height)} alt={label ?? "Molecule structure"}
               loading="lazy" onError={() => setFailed(true)} className="max-h-48 w-auto max-w-full" />
        )}
      </div>
      {label && <figcaption className="mt-1 text-center text-xs font-medium text-slate-600">{label}</figcaption>}
    </figure>
  );
}
