// Shared across docs/index.html and docs/compare.html: formatters, flags,
// and data loading. No build step - loaded directly with <script src="app.js">.

const $ = (id) => document.getElementById(id);
const usd = (n) => n.toLocaleString("en-US", {style:"currency", currency:"USD", maximumFractionDigits:0});
// For the amount the user actually typed/picked - never round it. usd()
// rounding $1.50 to "$2" in "Send $2 to..." would silently show a different
// number than the one they chose. Only the amount itself uses this; derived
// figures (loss, kept, fees) stay whole-dollar via usd() as before.
const usdPrecise = (n) => {
  const cents = Math.round(n * 100) % 100 !== 0;
  return n.toLocaleString("en-US", {style:"currency", currency:"USD", minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: 2});
};
const local = (n, c) => n.toLocaleString("en-US", {maximumFractionDigits:0}) + " " + c;
const esc = (s) => String(s).replace(/[<>&"]/g, ch => ({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[ch]));

// NOT a cosmetic rounding fix - this hides real reference-rate error, on
// purpose, up to a known limit. A provider whose rate beats our reference
// mid-market rate produces a negative "lost" figure. Above 1% disagreement
// (collect.py's RATE_DISAGREEMENT_THRESHOLD), that's surfaced explicitly via
// rate_uncertain + the banner/tag UI. BELOW 1%, there is no banner, and this
// clamp silently turns any resulting negative into "$0 you lose" - e.g. COP
// has measured at 0.90% disagreement with a provider computing to -0.12%,
// which displays as "$0" with no indication it's a reference-rate artifact
// rather than a genuinely markup-free transfer. That gap is real, not
// eliminated - it's just below the threshold considered worth disclosing.
// See CLAUDE.md known gap #5 before raising or removing this threshold.
const usdLoss = (n) => usd(Math.max(0, n));

const C = {ink:"#17211d", inkSoft:"#3c453e", kept:"#9e2b3b", keptText:"#7a1f2c", best:"#1e6e52", bestText:"#14503b"};
const CW = 340; // shared chart viewBox width — keeps text scaling predictable across charts

// Simple geometric flags — no emoji, each has a <title> for screen readers.
const FLAGS = {
  BDT: `<title>Flag of Bangladesh</title><rect width="30" height="20" fill="#006a4e"/><circle cx="13" cy="10" r="6" fill="#f42a41"/>`,
  INR: `<title>Flag of India</title><rect width="30" height="20" fill="#fff"/><rect width="30" height="6.67" fill="#ff9933"/><rect y="13.33" width="30" height="6.67" fill="#138808"/><circle cx="15" cy="10" r="2.3" fill="none" stroke="#0000a0" stroke-width="0.7"/>`,
  PKR: `<title>Flag of Pakistan</title><rect width="30" height="20" fill="#01411c"/><rect width="7.5" height="20" fill="#fff"/><circle cx="20" cy="9" r="4" fill="#fff"/><circle cx="21.6" cy="8" r="3.4" fill="#01411c"/><rect x="23.3" y="8.3" width="1.4" height="1.4" fill="#fff" transform="rotate(45 24 9)"/>`,
  MXN: `<title>Flag of Mexico</title><rect width="30" height="20" fill="#fff"/><rect width="10" height="20" fill="#006341"/><rect x="20" width="10" height="20" fill="#ce1126"/>`,
  PHP: `<title>Flag of the Philippines</title><rect width="30" height="20" fill="#0038a8"/><rect y="10" width="30" height="10" fill="#ce1126"/><path d="M0 0 L13 10 L0 20 Z" fill="#fff"/><circle cx="5" cy="10" r="2.2" fill="#fcd116"/>`,
  DOP: `<title>Flag of the Dominican Republic</title><rect width="30" height="20" fill="#fff"/><rect width="13" height="8" fill="#002d62"/><rect x="17" width="13" height="8" fill="#ce1126"/><rect width="13" y="12" height="8" fill="#ce1126"/><rect x="17" y="12" width="13" height="8" fill="#002d62"/>`,
  // Nepal is the only non-rectangular national flag (two stacked pennants) —
  // drawn as a simplified silhouette, centered in the same fixed-size box as
  // every rectangular flag so the button grid still lines up.
  NPR: `<title>Flag of Nepal</title><path d="M9,1 L23,6 L14,10 L23,14 L9,19 Z" fill="#dc143c" stroke="#003893" stroke-width="1.3" stroke-linejoin="round"/><circle cx="16" cy="6" r="2.1" fill="#fff"/><circle cx="16.9" cy="5.3" r="1.7" fill="#dc143c"/><circle cx="16" cy="14" r="1.7" fill="#fff"/><circle cx="16" cy="14" r="3" fill="none" stroke="#fff" stroke-width="0.6"/>`,
  VND: `<title>Flag of Vietnam</title><rect width="30" height="20" fill="#da251d"/><path d="M15,5 L16.18,8.38 L19.76,8.45 L16.9,10.62 L17.94,14.05 L15,12 L12.06,14.05 L13.1,10.62 L10.24,8.45 L13.82,8.38 Z" fill="#ff0"/>`,
  GTQ: `<title>Flag of Guatemala</title><rect width="30" height="20" fill="#4997d0"/><rect x="10" width="10" height="20" fill="#fff"/>`,
  COP: `<title>Flag of Colombia</title><rect width="30" height="20" fill="#fcd116"/><rect y="10" width="30" height="5" fill="#003893"/><rect y="15" width="30" height="5" fill="#ce1126"/>`,
  NGN: `<title>Flag of Nigeria</title><rect width="30" height="20" fill="#008751"/><rect x="10" width="10" height="20" fill="#fff"/>`,
  HNL: `<title>Flag of Honduras</title><rect width="30" height="20" fill="#0073cf"/><rect y="6.67" width="30" height="6.67" fill="#fff"/><circle cx="15" cy="10" r="0.7" fill="#0073cf"/><circle cx="12" cy="8.3" r="0.7" fill="#0073cf"/><circle cx="18" cy="8.3" r="0.7" fill="#0073cf"/><circle cx="12" cy="11.7" r="0.7" fill="#0073cf"/><circle cx="18" cy="11.7" r="0.7" fill="#0073cf"/>`,
  EGP: `<title>Flag of Egypt</title><rect width="30" height="20" fill="#ce1126"/><rect y="6.67" width="30" height="6.67" fill="#fff"/><rect y="13.33" width="30" height="6.67" fill="#000"/>`,
  CNY: `<title>Flag of China</title><rect width="30" height="20" fill="#de2910"/><path d="M8,3.7 L8.53,5.27 L10.19,5.29 L8.86,6.28 L9.35,7.86 L8,6.9 L6.65,7.86 L7.14,6.28 L5.81,5.29 L7.47,5.27 Z" fill="#ffde00"/><circle cx="13" cy="3" r="0.5" fill="#ffde00"/><circle cx="14.5" cy="5.5" r="0.5" fill="#ffde00"/><circle cx="13.5" cy="8.5" r="0.5" fill="#ffde00"/><circle cx="11" cy="10" r="0.5" fill="#ffde00"/>`,
  PEN: `<title>Flag of Peru</title><rect width="30" height="20" fill="#d91023"/><rect x="10" width="10" height="20" fill="#fff"/>`,
  JMD: `<title>Flag of Jamaica</title><rect width="30" height="20" fill="#009b3a"/><polygon points="0,0 0,20 15,10" fill="#000"/><polygon points="30,0 30,20 15,10" fill="#000"/><line x1="0" y1="0" x2="30" y2="20" stroke="#fed100" stroke-width="4.5"/><line x1="0" y1="20" x2="30" y2="0" stroke="#fed100" stroke-width="4.5"/>`,
};

function flagMarkup(dst){
  if (FLAGS[dst]) return `<svg class="flag" viewBox="0 0 30 20" aria-hidden="true">${FLAGS[dst]}</svg>`;
  return `<span class="flagFallback" aria-hidden="true">${esc(dst.slice(0,2).toUpperCase())}</span>`;
}

// "2 hours ago" / "3 minutes ago", so a corridor collected on a slower
// schedule never reads as if it were just checked.
const RTF = new Intl.RelativeTimeFormat("en", {numeric:"auto"});
function freshness(iso){
  if (!iso) return "";
  const mins = Math.round((new Date(iso).getTime() - Date.now()) / 60000);
  if (Math.abs(mins) < 1) return "just now";
  if (Math.abs(mins) < 60) return RTF.format(mins, "minute");
  const hours = Math.round(mins / 60);
  if (Math.abs(hours) < 24) return RTF.format(hours, "hour");
  return RTF.format(Math.round(hours / 24), "day");
}

async function fetchSnapshot(){
  const r = await fetch("data/latest.json", {cache:"no-store"});
  if (!r.ok) throw new Error(String(r.status));
  const snap = await r.json();
  if (!snap.corridors?.length) throw new Error("empty");
  return snap;
}

// Hand-maintained receiving-government incentives (see scripts/incentives.json).
// Never folded into "what arrives" - always shown as its own line, since it's
// paid by a different party, often days later, and only to eligible transfers.
async function fetchIncentives(){
  try {
    const r = await fetch("data/incentives.json", {cache:"no-store"});
    return r.ok ? await r.json() : {};
  } catch { return {}; }
}

// received is in destination currency, mid is dst-per-USD. Returns null if
// this corridor has no confirmed incentive.
function incentiveFor(incentives, dst, received, mid){
  const inc = incentives[dst];
  if (!inc) return null;
  const localAmt = inc.kind === "percentage" ? received * (inc.rate / 100) : inc.rate;
  return {...inc, localAmt, usdAmt: localAmt / mid};
}

const HIST = {};
async function fetchHistory(key){
  if (!(key in HIST)) {
    try {
      const r = await fetch(`data/history/${key}.json`, {cache:"no-store"});
      HIST[key] = r.ok ? await r.json() : [];
    } catch { HIST[key] = []; }
  }
  return HIST[key];
}

function nearestBracket(quotes, amt){
  const keys = Object.keys(quotes).map(Number).sort((a,b)=>a-b);
  return String(keys.reduce((best,k) =>
    Math.abs(k-amt) < Math.abs(best-amt) ? k : best, keys[0]));
}

// The JSON's "lost" field is in the destination currency, not USD — convert
// using the ratio (lost/ideal), which is currency-independent, before ever
// showing a dollar figure to the user. usdLost can be negative (a provider
// beat the reference rate) - callers displaying it must use usdLoss() to
// clamp for display; this raw value is what sorting and differences use.
//
// At very small amounts, a provider's flat fee can consume most or all of
// the transfer (e.g. a $1 send against a $0.99 fee delivers about half a
// unit of foreign currency - technically a positive number, not the "free
// transfer" a literal $0 clamp would imply, but just as much nonsense to
// rank as a normal option). Such quotes are marked impractical instead of
// ranked normally; callers must check this before rendering a quote as a
// normal option (see index.html/compare.html for the "not available below
// about $X" treatment).
//
// IMPRACTICAL_FEE_SHARE is a judgment call, not an objective line - there
// is no fee-to-amount ratio that is *the* correct cutoff, only ones that
// are more or less defensible. 0.5 means: if the fee eats half or more of
// what you're sending, this isn't a real comparison point regardless of
// the exact cents delivered. Chosen because it's a round, explainable
// share ("more than half your money goes to the fee alone") rather than
// because it was derived from data. A stricter or looser share could be
// argued for; this one at least produces sane output instead of ranking
// a $0.58-delivered quote as a normal "Priciest" option (verified against
// DOP: Western Union's $0.99 fee against $1 sent no longer appears as a
// ranked row - see CLAUDE.md/commit history for the before/after).
const IMPRACTICAL_FEE_SHARE = 0.5;

function rowsFor(c, amt){
  const ideal = amt * c.mid;
  return (c.quotes[nearestBracket(c.quotes, amt)] || [])
    .map(q => {
      const impractical = q.fee >= amt * IMPRACTICAL_FEE_SHARE;
      const received = Math.max(0, (amt - q.fee) * q.rate);
      const lost = ideal - received;
      return {...q, received, usdLost: amt * (lost / ideal), impractical};
    })
    .sort((a,b) => (a.impractical - b.impractical) || (a.usdLost - b.usdLost));
}
