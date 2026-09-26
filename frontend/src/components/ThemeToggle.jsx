import { useEffect, useState } from "react";

const KEY = "theme";

function initialTheme() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "dark" || saved === "light") return saved;
  } catch { /* storage unavailable */ }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    try { localStorage.setItem(KEY, theme); } catch { /* ignore */ }
  }, [theme]);

  const dark = theme === "dark";
  return (
    <button type="button" onClick={() => setTheme(dark ? "light" : "dark")}
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"} aria-pressed={dark}
            className="ml-auto rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:border-indigo-400 hover:text-slate-900">
      {dark ? "☀ Light" : "🌙 Dark"}
    </button>
  );
}
