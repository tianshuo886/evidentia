#!/usr/bin/env python3
"""Freeze gate: coverage audit + manifest for a paper-read output dir.

Usage: python freeze_check.py --out <out>
Checks model/paper_model.json + evidence_graph.json exist, every inventory
figure/table inspected (role/depth assigned), every claim grounded, unresolved
listed. Writes model/manifest.json with sha256 + counts, status FROZEN or FAIL.
Exit 0 on FROZEN, 1 otherwise. Fix the model, never loosen the check.
"""
import argparse, hashlib, json, os, sys

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = a.out
    errs = []
    def load(p):
        if not os.path.exists(p):
            errs.append(f"missing {p}")
            return None
        try:
            with open(p) as f:
                return json.load(f)
        except Exception as e:
            errs.append(f"unparseable {p}: {e}")
            return None
    inv = load(f"{out}/model/figure_inventory.json") or {}
    pm = load(f"{out}/model/paper_model.json")
    eg = load(f"{out}/model/evidence_graph.json")
    items = inv.get("items", [])
    uninspected = [i["id"] for i in items
                   if i.get("role") in (None, "unassigned")
                   or i.get("depth") in (None, "unassigned")]
    if uninspected:
        errs.append(f"uninspected figures/tables: {uninspected}")
    claims = (pm or {}).get("claims", []) if pm else []
    ung = [c.get("id") for c in claims
           if not c.get("evidence") and c.get("epistemic") not in ("NOT_STATED",)]
    if ung:
        errs.append(f"claims without evidence: {ung}")
    figs_dir = f"{out}/assets/figures"
    missing_files = [i["id"] for i in items
                     if i.get("role") == "critical" and not i.get("file")
                     and not os.path.isdir(figs_dir)]
    total_fig = sum(1 for i in items if i.get("kind") == "figure")
    total_tab = sum(1 for i in items if i.get("kind") == "table")
    man = {
        "figures_total": total_fig,
        "tables_total": total_tab,
        "figures_inspected": total_fig - sum(1 for i in items
            if i.get("kind") == "figure" and i["id"] in uninspected),
        "claims": len(claims),
        "unresolved_claims": sum(1 for c in claims
            if c.get("epistemic") in ("UNRESOLVED", "INSUFFICIENT_EVIDENCE", "AMBIGUOUS")),
        "errors": errs,
        "status": "FROZEN" if not errs and pm and eg is not None else "FAIL",
    }
    for key, p in (("paper_sha256", f"{out}/source/paper.pdf"),
                   ("paper_model_sha256", f"{out}/model/paper_model.json"),
                   ("evidence_graph_sha256", f"{out}/model/evidence_graph.json")):
        if os.path.exists(p):
            man[key] = sha(p)
    with open(f"{out}/model/manifest.json", "w") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    print(("FROZEN " if man["status"] == "FROZEN" else "FAIL ") + json.dumps(man, ensure_ascii=False))
    sys.exit(0 if man["status"] == "FROZEN" else 1)

if __name__ == "__main__":
    main()
