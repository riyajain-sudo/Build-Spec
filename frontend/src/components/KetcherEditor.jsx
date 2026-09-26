import { Editor } from "ketcher-react";
import { StandaloneStructServiceProvider } from "ketcher-standalone";
import "ketcher-react/dist/index.css";

const structServiceProvider = new StandaloneStructServiceProvider();

// Loaded lazily (see MoleculeInput) because Ketcher is a large bundle.
export default function KetcherEditor({ onReady }) {
  return (
    <div className="h-[520px] overflow-hidden rounded-lg border border-slate-300 bg-white">
      <Editor
        staticResourcesUrl=""
        structServiceProvider={structServiceProvider}
        errorHandler={(msg) => console.error("Ketcher:", msg)}
        onInit={(ketcher) => onReady(ketcher)}
      />
    </div>
  );
}
