#!/usr/bin/env python3
"""Reproduce every number, table and figure of the TokWatt paper from data/.

Usage:   python paper/analysis.py
Writes:  paper/generated/stats.tex      LaTeX macros used in the text
         paper/generated/tab_*.tex      tables
         paper/figures/fig_*.pdf        figures
"""
import csv
import math
import os
import statistics
from decimal import ROUND_HALF_UP, Decimal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
GEN = os.path.join(ROOT, "paper", "generated")
FIG = os.path.join(ROOT, "paper", "figures")
os.makedirs(GEN, exist_ok=True)
os.makedirs(FIG, exist_ok=True)


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(x):
    return None if x in ("", None) else float(x)


def sig(v, n=2):
    """Round half-up to n significant figures (as the app does), with thousands separators."""
    if v is None or not math.isfinite(v):
        return "--"
    if v == 0:
        return "0"
    d = n - 1 - math.floor(math.log10(abs(v)))
    q = Decimal(repr(v)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    if d <= 0:
        return f"{int(q):,}"
    return f"{q:.{d}f}"


def ref(v):
    """House style for energy values: 2 significant figures below 100, 3 from 100 up."""
    return sig(v, 3 if v >= 100 else 2)


def rng(lo, hi):
    return "--" if abs(hi - lo) <= 1e-12 * max(1.0, abs(hi)) else f"{ref(lo)}--{ref(hi)}"


EST = read("estimates.csv")
SRC = {r["source_id"]: r for r in read("sources.csv")}
TASKS = {r["task_id"]: r for r in read("tasks.csv")}
DEFS = {r["task_id"]: r for r in read("task_defaults.csv")}
MACRO = read("macro.csv")
PAR = {r["parameter"]: float(r["value"]) for r in read("parameters.csv")}
GRID = read("grid_carbon.csv")
TF = read("token_factors.csv")
EQ = read("equivalents.csv")
F_ACC, PUE = PAR["F_ACCELERATOR_TO_FULL"], PAR["PUE_REF"]

BIB = {  # source_id -> BibTeX key in paper/references.bib
    "GOOGLE2025": "elsworth2025measuring", "ALTMAN2025": "altman2025gentle", "EPOCH2025": "you2025chatgpt",
    "OVIEDO2026": "oviedo2026energy", "JEGHAM2025": "jegham2025hungry", "LUCCIONI2024": "luccioni2024power",
    "MITTR2025": "odonnell2025math", "HFVIDEO2025": "delavande2025videoblog", "MISTRAL2025": "mistral2025lca",
    "DEVRIES2023": "devries2023growing", "COUCH2026": "couch2026agents", "HAUSFATHER2026": "hausfather2026agentic",
    "MLENERGY2025": "chung2025mlenergy",
}
TYPE = {
    "company_research_preprint": "Company study", "company_disclosure": "Company statement", "research_newsletter": "Research note",
    "peer_reviewed_article": "Journal article", "preprint": "Preprint", "peer_reviewed_conference": "Conference paper",
    "journalism_with_measurements": "Journalism", "benchmark_blog": "Benchmark report", "company_lca": "Company LCA",
    "peer_reviewed_commentary": "Commentary", "blog_estimate": "Analyst estimate",
}
METHOD = {
    "measured": "measured", "modeled": "modeled", "disclosed": "disclosed", "estimated_from_tokens": "token-based",
    "lca": "LCA", "measured_gpu_x2_heuristic": "GPU $\\times$2", "secondary_report": "secondary",
}
FAMILY_ORDER = ["text", "agentic", "image", "video", "classic"]


# ---------------------------------------------------------------- harmonization (mirrors scripts/build.py)
def factor(r, f_acc=F_ACC, pue=PUE):
    if num(r["energy_wh"]) is None and num(r["energy_wh_low"]) is None:
        return None
    if r["method"] == "measured_gpu_x2_heuristic":
        return 1.0
    if r["incl_accelerator"] == "yes" and r["incl_host"] == "no":
        return f_acc
    if r["incl_host"] in ("yes", "approx") and r["incl_overhead_pue"] == "no":
        return pue
    return 1.0


def bounds(r):
    p, sd = num(r["energy_wh"]), num(r["energy_wh_sd"])
    lo, hi = num(r["energy_wh_low"]), num(r["energy_wh_high"])
    lo = lo if lo is not None else (max(0.0, p - sd) if sd is not None else p)
    hi = hi if hi is not None else (p + sd if sd is not None else p)
    return lo, hi


def defaults(f_acc=F_ACC, pue=PUE):
    out = {}
    for tid in TASKS:
        rows = [r for r in EST if r["task"] == tid and num(r["energy_wh"]) is not None]
        ref = [r for r in rows if r["in_reference_set"] == "TRUE"]
        if not ref:
            continue
        pts, lows, highs = [], [], []
        for r in ref:
            f = factor(r, f_acc, pue)
            lo, hi = bounds(r)
            pts.append(num(r["energy_wh"]) * f)
            lows.append(lo * f)
            highs.append(hi * f)
        allpts = [num(r["energy_wh"]) * factor(r, f_acc, pue) for r in rows]
        out[tid] = dict(c=statistics.median(pts), lo=min(lows), hi=max(highs), n=len(ref),
                        ns=len({r["source_id"] for r in ref}), allmed=statistics.median(allpts), nall=len(rows))
    return out


BASE = defaults()
for tid, d in BASE.items():  # the paper must agree with the released table
    assert abs(d["c"] - float(DEFS[tid]["central_wh"])) <= 1e-3 * max(1, d["c"]), tid

S = {}


def put(name, value):
    assert name.isalpha() and name not in S, name
    S[name] = str(value)


# ---------------------------------------------------------------- composition
energy = [r for r in EST if num(r["energy_wh"]) is not None]
src_est = sorted({r["source_id"] for r in EST})
put("nEst", len(EST))
put("nEstEnergy", len(energy))
put("nSrcEst", len(src_est))
put("nSrcAll", len(SRC))
put("nTasks", len(TASKS))
put("nTasksRef", len(BASE))
put("nRefRows", sum(r["in_reference_set"] == "TRUE" for r in EST))
put("nModels", len({r["model"] for r in EST}))
put("nGrid", len(GRID))
put("nGridCountries", sum(1 for g in GRID if g["iso_code"]))
put("nGridRegions", sum(1 for g in GRID if not g["iso_code"]))
put("gridYearMin", min(int(g["year"]) for g in GRID))
put("gridYearMax", max(int(g["year"]) for g in GRID))
put("nMacro", len(MACRO))
put("nTokenFactors", len(TF))
put("nEquivalents", len(EQ))
mcount = {m: sum(r["method"] == m for r in EST) for m in METHOD}
for m, name in [("measured", "nMeasured"), ("modeled", "nModeled"), ("disclosed", "nDisclosed"), ("estimated_from_tokens", "nTokenBased"),
                ("lca", "nLCA"), ("measured_gpu_x2_heuristic", "nGpuTwo"), ("secondary_report", "nSecondary")]:
    put(name, mcount[m])
put("nProprietary", sum(r["model_access"] == "proprietary" for r in EST))
put("nOpenWeights", sum(r["model_access"] == "open-weights" for r in EST))
put("nSrcPeer", sum(SRC[s]["peer_reviewed"] == "yes" for s in src_est))
put("yearMin", min(int(SRC[s]["year"]) for s in src_est))
put("yearMax", max(int(SRC[s]["year"]) for s in src_est))
n_int = sum(1 for r in energy if any(r[k] for k in ("energy_wh_low", "energy_wh_high", "energy_wh_sd")))
put("nInterval", n_int)
put("pctInterval", sig(100 * n_int / len(energy), 2))
put("nTokenRows", sum(1 for r in EST if r["tokens_in"] or r["tokens_out"]))
put("nCOtwo", sum(1 for r in EST if r["co2e_g"]))
put("nWater", sum(1 for r in EST if r["water_ml"]))
unk = [r for r in energy if "unknown" in (r["incl_accelerator"], r["incl_host"], r["incl_overhead_pue"])]
put("nBoundaryUnknown", len(unk))
put("nBoundaryUnknownSrc", len({r["source_id"] for r in unk}))
fac = [factor(r) for r in energy]
put("nFacc", sum(1 for f in fac if abs(f - F_ACC) < 1e-9))
put("nFpue", sum(1 for f in fac if abs(f - PUE) < 1e-9))
put("nFone", sum(1 for f in fac if f == 1.0))
put("Facc", sig(F_ACC, 3))
put("PUEref", sig(PUE, 3))
put("WUEref", sig(PAR["WUE_ONSITE_L_PER_KWH"], 3))
put("priceUSD", f"{PAR['DEFAULT_PRICE_USD_PER_KWH']:.3f}")

# boundary coverage per component (rows with an energy value)
BND = {"incl_accelerator": "Acc", "incl_host": "Host", "incl_idle": "Idle", "incl_overhead_pue": "Pue", "incl_embodied": "Emb"}
for col, k in BND.items():
    put("bnd" + k + "Yes", sum(r[col] == "yes" for r in energy))
    put("bnd" + k + "Approx", sum(r[col] in ("approx", "partial") for r in energy))
    put("bnd" + k + "No", sum(r[col] == "no" for r in energy))
    put("bnd" + k + "Unknown", sum(r[col] == "unknown" for r in energy))
full = [r for r in energy if all(r[c] in ("yes", "approx", "partial") for c in ("incl_accelerator", "incl_host", "incl_idle", "incl_overhead_pue"))]
put("nFullOperational", len(full))
put("nFullOperationalSrc", len({r["source_id"] for r in full}))
put("nAllUnknown", sum(all(r[c] == "unknown" for c in BND) for r in energy))
lca = next(r for r in EST if r["method"] == "lca")
put("lcaModel", lca["model"])

# verification status (the paper reports it as it stands in the data)
n_ver = sum(r["verification"] == "human_verified" for r in EST)
put("nVerified", n_ver)
if n_ver == len(EST):
    put("verificationSentence", f"The author then checked every row against the table, figure or section cited as its locator; all {len(EST)} rows carry the status \\texttt{{human\\_verified}} in the \\texttt{{verification}} field.")
else:
    put("verificationSentence", f"In the release described here, {n_ver} of {len(EST)} rows carry the status \\texttt{{human\\_verified}}; the others carry "
        "\\texttt{assistant\\_\\allowbreak{}extracted\\_\\allowbreak{}needs\\_\\allowbreak{}human\\_\\allowbreak{}check} and are treated as provisional until checked.")

# ---------------------------------------------------------------- consistency checks used in Technical Validation
g_narrow = next(r for r in EST if r["source_id"] == "GOOGLE2025" and r["incl_host"] == "no")
g_full = next(r for r in EST if r["source_id"] == "GOOGLE2025" and r["incl_host"] == "yes")
put("googleNarrow", sig(num(g_narrow["energy_wh"]), 2))
put("googleFull", sig(num(g_full["energy_wh"]), 2))
put("googleHarm", sig(num(g_narrow["energy_wh"]) * F_ACC, 2))
put("googleResidual", sig(num(g_narrow["energy_wh"]) * F_ACC / num(g_full["energy_wh"]), 2))
put("googleRatio", sig(num(g_full["energy_wh"]) / num(g_narrow["energy_wh"]), 2))
cluster_ids = [
    next(r for r in EST if r["source_id"] == "GOOGLE2025" and r["incl_host"] == "yes"),
    next(r for r in EST if r["source_id"] == "ALTMAN2025"),
    next(r for r in EST if r["source_id"] == "EPOCH2025" and r["task"] == "chat_short"),
    next(r for r in EST if r["source_id"] == "OVIEDO2026" and r["task"] == "chat_short"),
    next(r for r in EST if r["source_id"] == "JEGHAM2025" and r["model"] == "GPT-4o (Mar '25)" and r["prompt_size"] == "short"),
]
cv = [num(r["energy_wh"]) * factor(r) for r in cluster_ids]
put("clusterMin", sig(min(cv), 2))
put("clusterMax", sig(max(cv), 2))
put("clusterRatio", sig(max(cv) / min(cv), 2))
refset = [num(r["energy_wh"]) * factor(r) for r in energy if r["task"] == "chat_short" and r["in_reference_set"] == "TRUE"]
put("chatRefSpan", sig(max(refset) / min(refset), 2))
put("chatRefMax", ref(max(refset)))
chat_all = [num(r["energy_wh"]) * factor(r) for r in energy if r["task"] == "chat_short"]
put("chatAllN", len(chat_all))
put("chatAllMin", sig(min(chat_all), 2))
put("chatAllMax", sig(max(chat_all), 2))
put("chatAllRatio", sig(max(chat_all) / min(chat_all), 2))
jeg_long = [num(r["energy_wh"]) for r in EST if r["source_id"] == "JEGHAM2025" and r["prompt_size"] == "long"]
put("jeghamLongMax", sig(max(jeg_long), 3))

# ---------------------------------------------------------------- reference values and ratios
KEY = {"chat_short": "Chat", "chat_medium": "ChatMedium", "chat_reasoning": "Reason", "long_document": "Longdoc", "very_long_input": "Verylong",
       "agentic_task": "Agent", "agentic_coding_session": "Session", "agentic_coding_day": "Devday", "image_generation": "Image",
       "video_generation": "Video", "text_classification": "Textcls"}
for tid, k in KEY.items():
    d = BASE[tid]
    put("ref" + k, ref(d["c"]))
    put("ref" + k + "Lo", ref(d["lo"]))
    put("ref" + k + "Hi", ref(d["hi"]))
    put("ref" + k + "N", d["n"])
    put("ref" + k + "Ns", d["ns"])
chat = BASE["chat_short"]["c"]
for tid, k in [("chat_reasoning", "Reason"), ("long_document", "Longdoc"), ("image_generation", "Image"), ("video_generation", "Video"),
               ("agentic_task", "Agent"), ("agentic_coding_session", "Session"), ("agentic_coding_day", "Devday")]:
    put("ratio" + k, sig(BASE[tid]["c"] / chat, 2))
put("ratioChatTextcls", sig(chat / BASE["text_classification"]["c"], 2))
cmin = min(d["c"] for d in BASE.values())
cmax = max(d["c"] for d in BASE.values())
oom = math.log10(cmax / cmin)
put("oom", sig(oom, 2))
put("oomWord", ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight"][round(oom)])
put("minTaskLabel", next(TASKS[t]["label"] for t, d in BASE.items() if d["c"] == cmin).lower())
put("maxTaskLabel", next(TASKS[t]["label"] for t, d in BASE.items() if d["c"] == cmax).lower())
put("refMin", ref(cmin))
put("refMax", ref(cmax))
single = [t for t, d in BASE.items() if d["ns"] == 1]
put("nSingleSource", len(single))

# ---------------------------------------------------------------- further text values
put("nBoundaryComp", len(read("boundary_components.csv")))
put("nParams", len(PAR))
mit = [num(r["energy_wh"]) for r in EST if r["source_id"] == "MITTR2025" and r["task"] == "chat_short"]
put("mitLo", sig(min(mit), 1))
put("mitHi", sig(max(mit), 2))
put("nJegham", sum(r["source_id"] == "JEGHAM2025" for r in EST))
put("nChatJegham", sum(r["source_id"] == "JEGHAM2025" and r["task"] == "chat_short" and r["in_reference_set"] == "TRUE" for r in EST))
put("nReasonJegham", sum(r["source_id"] == "JEGHAM2025" and r["task"] == "chat_reasoning" and r["in_reference_set"] == "TRUE" for r in EST))
for tid, k in [("chat_reasoning", "Reason"), ("image_generation", "Image"), ("video_generation", "Video"), ("chat_short", "Chat")]:
    put("span" + k, sig(BASE[tid]["hi"] / BASE[tid]["lo"], 2))
tfc = {r["token_type"]: float(r["wh_per_million_tokens"]) for r in TF if r["source_id"] == "COUCH2026" and "Opus" in r["model"]}
put("tfIn", f"{tfc['input (fresh)']:,.0f}")
put("tfOut", f"{tfc['output']:,.0f}")
put("tfCache", f"{tfc['cache read']:,.0f}")
put("tfRatio", sig(tfc["output"] / tfc["input (fresh)"], 1))
sess = [num(r["energy_wh"]) for r in EST if r["task"] == "agentic_coding_session" and r["in_reference_set"] == "TRUE"]
put("sessionLo", ref(min(sess)))
put("sessionHi", ref(max(sess)))
put("sessionRatio", sig(max(sess) / min(sess), 2))

# ---------------------------------------------------------------- macro context
def mv(ind, region, year, src, field="value"):
    rows = [m for m in MACRO if m["indicator"] == ind and m["region"] == region and m["year"] == year and m["source_id"] == src]
    assert len(rows) == 1, (ind, region, year, src)
    return float(rows[0][field])


def tw(v):
    return f"{v:,.0f}"


dc26 = mv("data_centre_electricity", "World", "2026", "GARTNER2026")
put("ieaTwhA", tw(mv("data_centre_electricity", "World", "2024", "IEA2025")))
put("ieaShare", sig(mv("data_centre_electricity_share", "World", "2024", "IEA2025"), 2))
put("ieaTwhB", tw(mv("data_centre_electricity", "World", "2030", "IEA2025")))
put("gartnerTwhA", tw(mv("data_centre_electricity", "World", "2025", "GARTNER2026")))
put("gartnerTwhB", tw(dc26))
put("gartnerGrowth", sig(100 * (dc26 / mv("data_centre_electricity", "World", "2025", "GARTNER2026") - 1), 2))
put("gartnerAIShare", sig(mv("ai_optimized_server_share_of_dc_consumption", "World", "2026", "GARTNER2026"), 2))
put("gartnerAITwh", tw(mv("ai_optimized_server_electricity", "World", "2026", "GARTNER2026")))
put("gartnerGW", tw(mv("data_centre_power_demand", "World", "2026", "GARTNER2026")))
put("gartnerTwhC", tw(mv("data_centre_electricity", "World", "2030", "GARTNER2026")))
put("lbnlTwh", tw(mv("data_centre_electricity", "United States", "2023", "LBNL2024")))
put("lbnlShare", sig(mv("data_centre_electricity_share", "United States", "2023", "LBNL2024"), 2))
put("lbnlTwhLo", tw(mv("data_centre_electricity", "United States", "2028", "LBNL2024", "value_low")))
put("lbnlTwhHi", tw(mv("data_centre_electricity", "United States", "2028", "LBNL2024", "value_high")))
put("lbnlShareLo", sig(mv("data_centre_electricity_share", "United States", "2028", "LBNL2024", "value_low"), 2))
put("lbnlShareHi", sig(mv("data_centre_electricity_share", "United States", "2028", "LBNL2024", "value_high"), 2))
put("dcAvgGW", sig(dc26 / 8.76, 3))

# today's chat volume, for scale (OpenAI statement reported by MIT Technology Review)
msgs = mv("chatgpt_messages_per_day", "World", "2024-12", "MITTR2025")
imgs = mv("chatgpt_images_per_day", "World", "2025-03", "MITTR2025")
put("chatgptMsgs", sig(msgs / 1e9, 1))
put("chatgptMW", sig(msgs * BASE["chat_short"]["c"] / 24 / 1e6, 2))
put("chatgptImgsM", sig(imgs / 1e6, 2))
put("chatgptImgMW", sig(imgs * BASE["image_generation"]["c"] / 24 / 1e6, 2))

# ---------------------------------------------------------------- usage profiles (illustrative)
PROFILES = [
    ("Occasional chat", {"chat_short": 5}),
    ("Daily chat", {"chat_short": 20, "chat_reasoning": 3}),
    ("Calculator example day", {"chat_short": 20, "chat_reasoning": 3, "long_document": 1, "agentic_task": 1, "image_generation": 2}),
    ("Knowledge work", {"chat_short": 30, "chat_reasoning": 10, "long_document": 5}),
    ("Image and video creation", {"chat_short": 20, "image_generation": 20, "video_generation": 2}),
    ("Agent-assisted development", {"chat_short": 20, "agentic_task": 10}),
]
LABEL_SHORT = {"chat_short": "chat", "chat_reasoning": "reasoning", "long_document": "long doc.", "agentic_task": "agent",
               "image_generation": "image", "video_generation": "video"}


def profile(counts, base=BASE):
    c = sum(n * base[t]["c"] for t, n in counts.items())
    lo = sum(n * base[t]["lo"] for t, n in counts.items())
    hi = sum(n * base[t]["hi"] for t, n in counts.items())
    return c, lo, hi


prof_rows = []
for name, counts in PROFILES:
    c, lo, hi = profile(counts)
    prof_rows.append((name, counts, c, lo, hi))
ex = next(p for p in prof_rows if p[0] == "Calculator example day")
put("exDayWh", ref(ex[2]))
put("exDayLo", ref(ex[3]))
put("exDayHi", ref(ex[4]))
put("exDayGW", sig(ex[2] / 24, 2))
put("exDayTWh", sig(ex[2] * 0.365, 2))
put("exDayPctDC", sig(100 * ex[2] * 0.365 / dc26, 2))
put("exAgentShare", sig(100 * BASE["agentic_task"]["c"] / ex[2], 2))
dev = next(p for p in prof_rows if p[0] == "Agent-assisted development")
put("devGW", sig(dev[2] / 24, 2))
put("devPctDC", sig(100 * dev[2] * 0.365 / dc26, 2))
occ = next(p for p in prof_rows if p[0] == "Occasional chat")
put("occGW", sig(occ[2] / 24, 2))
put("occMW", sig(occ[2] / 24 * 1000, 2))

# ---------------------------------------------------------------- sensitivity
SCEN = [("Baseline", F_ACC, PUE), (f"$F={2.0:g}$", 2.0, PUE), ("PUE 1.09", F_ACC, 1.09), ("PUE 1.27", F_ACC, 1.27), ("None", 1.0, 1.0)]
SENS_TASKS = ["chat_short", "chat_reasoning", "long_document", "agentic_task", "image_generation", "video_generation", "text_classification"]
sens = {name: defaults(f, p) for name, f, p in SCEN}
maxdev = 0.0
for name, _, _ in SCEN[1:]:
    for t in SENS_TASKS:
        maxdev = max(maxdev, abs(sens[name][t]["c"] / BASE[t]["c"] - 1))
put("sensMaxPct", sig(100 * maxdev, 2))
vid_lo = sens["PUE 1.09"]["video_generation"]["c"]
vid_hi = sens["PUE 1.27"]["video_generation"]["c"]
put("sensVideoLo", ref(vid_lo))
put("sensVideoHi", ref(vid_hi))
put("sensVideoNone", ref(sens["None"]["video_generation"]["c"]))
invariant = [t for t in SENS_TASKS if all(abs(sens[n][t]["c"] - BASE[t]["c"]) < 1e-9 for n, _, _ in SCEN)]
put("nInvariant", len(invariant))
NOUN = {"chat_short": "short chat answers", "chat_reasoning": "reasoning answers", "long_document": "long-document chat",
        "agentic_task": "agent tasks", "image_generation": "image generation", "video_generation": "video generation",
        "text_classification": "text classification"}
changed = [NOUN[t] for t in SENS_TASKS if t not in invariant]
put("sensChangedTasks", " and ".join([", ".join(changed[:-1]), changed[-1]]) if len(changed) > 1 else changed[0])
put("nSensChanged", len(changed))
allmed_chat = BASE["chat_short"]["allmed"]
put("chatAllMedian", ref(allmed_chat))
put("nSensTasks", len(SENS_TASKS))

# ---------------------------------------------------------------- tables
def esc(s):
    return s.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")


def write(name, text):
    with open(os.path.join(GEN, name), "w", encoding="utf-8") as f:
        f.write("% generated by paper/analysis.py -- do not edit\n" + text)


# sources contributing estimates
lines = []
for sid in sorted(src_est, key=lambda s: (-sum(r["source_id"] == s for r in EST), SRC[s]["year"])):
    rows = [r for r in EST if r["source_id"] == sid]
    fams = sorted({TASKS[r["task"]]["family"] for r in rows}, key=FAMILY_ORDER.index)
    meths = sorted({METHOD[r["method"]] for r in rows})
    pr = {"yes": "yes", "no": "no", "third_party_review": "external"}[SRC[sid]["peer_reviewed"]]
    lines.append(f"\\citet{{{BIB[sid]}}} & {TYPE[SRC[sid]['source_type']]} & {pr} & {', '.join(meths)} & {', '.join(fams)} & {len(rows)} \\\\")
RX = ">{\\raggedright\\arraybackslash}X"
write("tab_sources.tex", f"\\setlength{{\\tabcolsep}}{{4.5pt}}\n\\begin{{tabularx}}{{\\linewidth}}{{@{{}}{RX} l l {RX} l r@{{}}}}\n\\toprule\n"
      "Source & Type & Peer review & Method & Task families & $n$ \\\\\n\\midrule\n"
      + "\n".join(lines) + f"\n\\midrule\nTotal & & & & & {len(EST)} \\\\\n\\bottomrule\n\\end{{tabularx}}\n")

# reference values
lines = []
for tid, d in sorted(BASE.items(), key=lambda kv: kv[1]["c"]):
    mark = "$^{\\dagger}$" if d["ns"] == 1 else ""
    span = rng(d["lo"], d["hi"])
    ratio = "--" if span == "--" else sig(d["hi"] / d["lo"], 2)
    lines.append(f"{esc(TASKS[tid]['label'])}{mark} & {ref(d['c'])} & {span} & {ratio} "
                 f"& {ref(d['allmed'])} & {d['n']} & {d['nall']} & {d['ns']} \\\\")
write("tab_reference.tex", "\\setlength{\\tabcolsep}{4.5pt}\n\\begin{tabular}{@{}l r r r r r r r@{}}\n\\toprule\n"
      "& Reference & Range & High/ & Median, & \\multicolumn{2}{c}{Estimates} & \\\\\n\\cmidrule(lr){6-7}\n"
      "Task & (Wh) & (Wh) & low & all rows (Wh) & ref.\\ set & all & Sources \\\\\n\\midrule\n"
      + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")

# sensitivity
head = " & ".join(n for n, _, _ in SCEN)
lines = []
for t in SENS_TASKS:
    cells = []
    for name, _, _ in SCEN:
        v = sens[name][t]["c"]
        cells.append(sig(v, 3))
    lines.append(f"{esc(TASKS[t]['label'])} & " + " & ".join(cells) + " \\\\")
# sensitivity cells keep three significant figures so that small shifts stay visible
write("tab_sensitivity.tex", "\\begin{tabular}{@{}l r r r r r@{}}\n\\toprule\nTask & " + head + " \\\\\n\\midrule\n" + "\n".join(lines)
      + "\n\\bottomrule\n\\end{tabular}\n")

# profiles
lines = []
for name, counts, c, lo, hi in prof_rows:
    use = ", ".join(f"{n} {LABEL_SHORT[t]}" for t, n in counts.items())
    lines.append(f"\\textbf{{{name}}}\\newline {use} & {ref(c)} & {rng(lo, hi)} & {sig(c / 24, 2)} & {sig(c * 0.365, 2)} & {sig(100 * c * 0.365 / dc26, 2)} \\\\")
write("tab_profiles.tex", "\\begin{tabularx}{\\linewidth}{@{}>{\\raggedright\\arraybackslash}X r r r r r@{}}\n\\toprule\n"
      "Profile and tasks per user per day & $E$ & Range & Power & Energy & Share of 2026 \\\\\n"
      "& (Wh/day) & (Wh/day) & (GW) & (TWh/yr) & DC use (\\%) \\\\\n\\midrule\n" + "\n".join(lines)
      + "\n\\bottomrule\n\\end{tabularx}\n")

with open(os.path.join(GEN, "stats.tex"), "w", encoding="utf-8") as f:
    f.write("% generated by paper/analysis.py -- do not edit\n")
    for k, v in S.items():
        f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")

# ---------------------------------------------------------------- figures
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.linewidth": 0.6, "pdf.fonttype": 42,
                     "xtick.major.width": 0.6, "ytick.major.width": 0, "axes.edgecolor": "#5F676B", "text.color": "#15191B",
                     "axes.labelcolor": "#15191B", "xtick.color": "#46494C", "ytick.color": "#15191B"})
AMBER, AMBER_WASH, GREY, INK, GRID_C = "#B86A00", "#EBCB9C", "#9CA09A", "#15191B", "#E1E4E1"
TICKS = [1e-3, 1e-2, 1e-1, 1, 10, 100, 1e3, 1e4]
TICKL = ["0.001", "0.01", "0.1", "1", "10", "100", "1,000", "10,000"]

# Figure 1: energy ladder
order = sorted(BASE, key=lambda t: BASE[t]["c"])
fig, ax = plt.subplots(figsize=(6.6, 5.0))
for i, t in enumerate(order):
    d = BASE[t]
    ax.hlines(i, d["lo"], d["hi"], color=AMBER_WASH, linewidth=5.5, capstyle="round", zorder=1)
    xs = [num(r["energy_wh"]) * factor(r) for r in energy if r["task"] == t]
    ax.scatter(xs, [i] * len(xs), s=11, color=GREY, edgecolors="white", linewidths=0.5, zorder=2)
    ax.scatter([d["c"]], [i], s=30, color=AMBER, edgecolors="white", linewidths=0.8, zorder=3)
    ax.text(max([d["hi"]] + xs) * 1.35, i, f"{ref(d['c'])} Wh", va="center", fontsize=6.6, color="#46494C")
ax.set_xscale("log")
ax.set_xlim(7e-4, 3e4)
ax.set_ylim(-0.7, len(order) - 0.3)
ax.set_yticks(range(len(order)))
ax.set_yticklabels([TASKS[t]["label"] for t in order])
ax.set_xticks(TICKS)
ax.set_xticklabels(TICKL)
ax.minorticks_off()
ax.grid(axis="x", color=GRID_C, linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.set_xlabel("Energy per task (Wh, logarithmic scale)")
ax.legend(handles=[Line2D([0], [0], color=AMBER_WASH, lw=5.5, solid_capstyle="round", label="Reference range"),
                   Line2D([0], [0], marker="o", color="w", markerfacecolor=AMBER, markersize=6.5, label="Reference value"),
                   Line2D([0], [0], marker="o", color="w", markerfacecolor=GREY, markersize=4.5, label="Individual estimate (harmonized)")],
          loc="lower right", frameon=False, fontsize=6.8)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_ladder.pdf"))
plt.close(fig)

# Figure 2: boundary coverage
COMP = [("incl_accelerator", "Accelerators"), ("incl_host", "Host server"), ("incl_idle", "Idle capacity"),
        ("incl_overhead_pue", "Facility overhead (PUE)"), ("incl_embodied", "Hardware manufacturing")]
STATES = [("yes", "counted", "#3A3F42", None), ("approx", "approximated or partial", "#9CA09A", None),
          ("no", "not counted", "#E1E4E1", None), ("unknown", "not stated", "#F6F7F6", "////")]
fig, ax = plt.subplots(figsize=(6.6, 1.9))
for i, (k, lab) in enumerate(COMP):
    left = 0
    for st, slab, col, hatch in STATES:
        n = sum(1 for r in energy if (r[k] in ("approx", "partial") if st == "approx" else r[k] == st))
        if n:
            ax.barh(i, n, left=left, color=col, edgecolor="white", hatch=hatch, hatchcolor="#9CA09A", linewidth=1.0, height=0.62)
            if n >= 9:
                ax.text(left + n / 2, i, str(n), ha="center", va="center", fontsize=6.6, color="white" if st == "yes" else INK)
        left += n
ax.set_yticks(range(len(COMP)))
ax.set_yticklabels([lab for _, lab in COMP])
ax.invert_yaxis()
ax.set_xlim(0, len(energy))
ax.set_xlabel(f"Number of estimates with an energy value (n = {len(energy)})")
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.legend(handles=[Patch(facecolor=c, edgecolor="white", hatch=h, hatchcolor="#9CA09A", linewidth=0.6, label=l) for _, l, c, h in STATES],
          loc="upper center", bbox_to_anchor=(0.5, 1.22), ncol=4, frameon=False, fontsize=6.8)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_boundary.pdf"))
plt.close(fig)

# Figure 3: why chat-answer estimates disagree
CHAT_SRC = ["DEVRIES2023", "MITTR2025", "MLENERGY2025", "JEGHAM2025", "OVIEDO2026", "EPOCH2025", "ALTMAN2025", "GOOGLE2025"]
NAMES = {"DEVRIES2023": "de Vries (2023)", "MITTR2025": "MIT Technology Review (2025)", "MLENERGY2025": "ML.ENERGY (2025)",
         "JEGHAM2025": "Jegham et al. (2025)", "OVIEDO2026": "Oviedo et al. (2026)", "EPOCH2025": "You / Epoch AI (2025)",
         "ALTMAN2025": "Altman / OpenAI (2025)", "GOOGLE2025": "Elsworth et al. / Google (2025)"}
fig, ax = plt.subplots(figsize=(6.6, 3.0))
for i, sid in enumerate(CHAT_SRC):
    rows = [r for r in energy if r["task"] == "chat_short" and r["source_id"] == sid]
    for r in rows:
        f = factor(r)
        v = num(r["energy_wh"]) * f
        lo, hi = bounds(r)
        inref = r["in_reference_set"] == "TRUE"
        if inref and hi > lo:
            ax.hlines(i, lo * f, hi * f, color=INK, linewidth=0.7, zorder=1)
        mk = "D" if f != 1.0 else "o"
        ax.scatter([v], [i], s=26 if inref else 13, marker=mk, color=AMBER if inref else GREY, edgecolors="white", linewidths=0.6,
                   zorder=3 if inref else 2)
ax.axvline(BASE["chat_short"]["c"], color=AMBER, linewidth=0.8, zorder=0)
ax.text(BASE["chat_short"]["c"] * 1.06, -0.45, f"reference value {ref(BASE['chat_short']['c'])} Wh", fontsize=6.4, color="#46494C", va="center")
ax.set_xscale("log")
ax.set_xlim(0.02, 6)
ax.set_xticks([0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5])
ax.set_xticklabels(["0.02", "0.05", "0.1", "0.2", "0.5", "1", "2", "5"])
ax.minorticks_off()
ax.set_yticks(range(len(CHAT_SRC)))
ax.set_yticklabels([NAMES[s] for s in CHAT_SRC])
ax.set_ylim(-0.6, len(CHAT_SRC) - 0.1)
ax.grid(axis="x", color=GRID_C, linewidth=0.6)
ax.set_axisbelow(True)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.set_xlabel("Energy per short chat answer (Wh, logarithmic scale, after harmonization)")
ax.legend(handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor=AMBER, markersize=6, label="In the reference set"),
                   Line2D([0], [0], color=INK, lw=0.7, label="Its reported interval"),
                   Line2D([0], [0], marker="o", color="w", markerfacecolor=GREY, markersize=4.5, label="Other estimate"),
                   Line2D([0], [0], marker="D", color="w", markerfacecolor=GREY, markersize=4, label="Scaled to the common boundary")],
          loc="upper center", bbox_to_anchor=(0.42, 1.16), ncol=4, frameon=False, fontsize=6.6)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_chat.pdf"))
plt.close(fig)

print(f"{len(S)} macros, 4 tables, 3 figures")
for k in ("nEst", "nEstEnergy", "nSrcEst", "nRefRows", "refChat", "refAgent", "refVideo", "oom", "exDayWh", "exDayGW", "exDayPctDC",
          "clusterRatio", "chatAllRatio", "googleResidual", "sensMaxPct", "nInvariant", "devPctDC", "nInterval", "pctInterval",
          "nBoundaryUnknown", "nFacc", "nFpue"):
    print(f"  {k} = {S[k]}")
