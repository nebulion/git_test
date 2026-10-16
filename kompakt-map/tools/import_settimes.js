// Build app/assets/lineup.json from the official III Points set-times bundle.
// Usage: node tools/import_settimes.js source/SetTimesPage.*.js source/ExperiencePage.*.js app/assets/lineup.json
const fs = require("fs");
const [setTimesJs, experienceJs, out] = process.argv.slice(2);

// Extract a JS object literal that starts right after `marker`.
function literalAfter(src, marker) {
  const i = src.indexOf(marker) + marker.length;
  let depth = 0, j = i, quote = null;
  for (; j < src.length; j++) {
    const c = src[j];
    if (quote) { if (c === "\\") { j++; continue; } if (c === quote) quote = null; continue; }
    if (c === "`" || c === '"' || c === "'") { quote = c; continue; }
    if (c === "{" || c === "[") depth++;
    else if (c === "}" || c === "]") { depth--; if (depth === 0) { j++; break; } }
  }
  return src.slice(i, j);
}

const st = fs.readFileSync(setTimesJs, "utf8");
const sets = Function("return " + literalAfter(st, "var s="))();
const order = Function("return " + literalAfter(st, ",u="))();

// Stage display names and hosts from the experience bundle ({id:`..`,name:`..`,color:..,host:`..`}).
const ex = fs.readFileSync(experienceJs, "utf8");
const meta = {};
for (const m of ex.matchAll(/\{id:`([a-z0-9-]+)`,name:`([^`]*)`,color:`[^`]*`,host:`([^`]*)`/g)) {
  meta[m[1]] = { name: m[2], host: m[3] };
}

// "11:30 PM" -> "23:30"; times after midnight belong to the previous festival day -> "25:30".
function hhmm(t) {
  const m = /(\d+):(\d+)\s*(AM|PM)/i.exec(t);
  let h = (+m[1]) % 12;
  if (/PM/i.test(m[3])) h += 12;
  if (h < 12) h += 24;
  return String(h).padStart(2, "0") + ":" + m[2];
}

const stages = order.map((id) => ({
  id,
  name: id === "444" ? "::444::" : (meta[id] || { name: id }).name,
  host: (meta[id] || {}).host || "",
  sets: Object.fromEntries(Object.keys(sets).map((day) => [day,
    ((sets[day].stages || {})[id] || []).map((x) => {
      const row = [hhmm(x.start), hhmm(x.end), x.name.trim()];
      const extra = [x.tag, x.note].filter(Boolean).join(" · ");
      if (extra) row.push(extra);
      return row;
    })])),
}));

const doc = {
  name: "III Points 2026",
  venue: "Mana Wynwood, Miami",
  timezone: "America/New_York",
  source: "Official set times, iiipoints.com/set-times (snapshot " + new Date().toISOString().slice(0, 10) + ")",
  days: [
    { id: "fri", label: "Fri", long: "Friday, Oct 16", date: "2026-10-16" },
    { id: "sat", label: "Sat", long: "Saturday, Oct 17", date: "2026-10-17" },
  ],
  stages,
};
fs.writeFileSync(out, JSON.stringify(doc, null, 1) + "\n");
console.log(stages.map((s) => `${s.name}: fri ${s.sets.fri.length}, sat ${s.sets.sat.length}`).join("\n"));
