"""Deterministic content parity and paper-only input auditing for release v2."""
import html
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

from intent_router import INTENT_INPUT_BOUNDARIES, enforce_task_firewall
from validate_common import load_json, schema_validate, sha256
from lens_execution_manifest import canonical_sha256, result_payload_sha256


def surface(text):
    text = unicodedata.normalize("NFKC", html.unescape(str(text or "")))
    # Strip actual markup tags without treating mathematical inequalities in
    # extracted PDF text (for example ``x < y``) as HTML.
    text = re.sub(r"</?[A-Za-z][^>]*>", " ", text)
    return re.sub(r"[\s\u00ad\u200b\ufeff`*_]+", "", text)


class ReaderHTML(HTMLParser):
    """Extract primary prose and exact local asset associations (no CSS/SVG text)."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.text = []
        self.all_text = []
        self.primary = False
        self.images = {}
        self.ids = []
        self.anchors = []
        self.equations = {}
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attr = dict(attributes)
        eid = attr.get("id", "")
        if eid:
            self.ids.append(eid)
        if tag == "a" and attr.get("href", "").startswith("#"):
            self.anchors.append(attr["href"][1:])
        if tag == "section" and eid.startswith("ch-"):
            self.primary = eid not in ("ch-sources", "ch-appendix")
        skip = tag in ("style", "script", "svg") or bool(set(attr.get("class", "").split()) & {"evidence-cite", "evidence-cites", "math-display", "eq-label"})
        parent_skip = any(x[2] for x in self.stack)
        container = eid.removeprefix("evidence-") if eid.startswith("evidence-") else next((x[1] for x in reversed(self.stack) if x[1]), None)
        if tag == "img" and container:
            self.images.setdefault(container, []).append(attr.get("src"))
        if tag == "svg" and container:
            self.equations[container] = self.equations.get(container, 0) + 1
        if tag not in self.VOID:
            self.stack.append((tag, container, skip or parent_skip))

    def handle_endtag(self, tag):
        for idx in range(len(self.stack)-1, -1, -1):
            if self.stack[idx][0] == tag:
                del self.stack[idx:]
                break

    def handle_data(self, data):
        if not any(x[2] for x in self.stack):
            self.all_text.append(data)
            if self.primary:
                self.text.append(data)


def parity_errors(root, manuscript, html_text, md_text, pdf_text):
    from render_paper_reader import render_paper_reader_html, render_paper_reader_md
    errors = []
    actual = ReaderHTML(html_text)
    expected = ReaderHTML(render_paper_reader_html(manuscript, root))
    if surface(" ".join(actual.text)) != surface(" ".join(expected.text)):
        errors.append("HTML semantic parity: primary prose differs from manuscript (added, missing, or changed scientific content)")
    if surface(md_text) != surface(render_paper_reader_md(manuscript, root)):
        errors.append("Markdown semantic parity: document differs from manuscript")
    pdf_surface = surface(pdf_text)
    for chapter in manuscript.get("document", {}).get("chapters", []):
        passages = [("title", chapter.get("title")), ("lead", chapter.get("lead"))]
        for idx, block in enumerate(chapter.get("blocks", []), 1):
            fields = ("text", "analysis", "explanation")
            if block.get("type") not in ("figure", "table"):
                fields = fields + ("caption",)
            for field in fields:
                if block.get(field):
                    passages.append((f"block {idx} {field}", block[field]))
            if block.get("type") == "list":
                passages.extend((f"block {idx} list item", item) for item in block.get("items", []))
            if block.get("type") in ("figure", "table", "equation"):
                eid = block.get("evidence_id")
                if surface(eid) not in pdf_surface:
                    errors.append(f"PDF semantic parity: {eid} evidence identifier missing")
                asset = block.get("asset") if block.get("type") != "equation" else block.get("fallback_asset")
                uses_fallback = block.get("type") != "equation" or block.get("source_confidence") != "VERIFIED"
                if uses_fallback and asset and f"../{asset}" not in actual.images.get(eid, []):
                    errors.append(f"HTML semantic parity: {eid} expected local source image is not rendered")
        for label, passage in passages:
            if passage and surface(passage) not in pdf_surface:
                errors.append(f"PDF semantic parity: {chapter.get('id')} {label} missing or changed")
    return errors


def lens_execution_provenance_errors(root):
    """Require core-issued, single-use receipts for every Reader-v3 Lens task."""
    root = Path(root)
    lens_tasks = sorted((root / "tasks/v3/lens").glob("*.json")) if (root / "tasks/v3/lens").exists() else []
    if not lens_tasks:
        return []
    errors = []
    seen_execution_ids = set()
    for task_path in lens_tasks:
        task = load_json(task_path)
        if not task.get("isolation_proof_required"):
            errors.append(f"Lens task lacks isolation_proof_required: {task_path.relative_to(root)}")
            continue
        task_id = task.get("task_id")
        task_sha = sha256(task_path)
        receipts = sorted((root / "agent_runs" / task_id).glob("receipt-*.json"))
        if len(receipts) != 1:
            errors.append(f"{task_id} requires exactly one core receipt, found {len(receipts)}")
            continue
        receipt_path = receipts[0]
        receipt = load_json(receipt_path)
        errors.extend(f"{task_id} receipt: {e}" for e in schema_validate(receipt, "execution_receipt"))
        if receipt.get("task_id") != task_id or receipt.get("task_sha256") != task_sha:
            errors.append(f"{task_id} receipt is not bound to the canonical task packet")
        execution_id = receipt.get("execution_id")
        if execution_id in seen_execution_ids:
            errors.append(f"duplicate Lens execution_id: {execution_id}")
        seen_execution_ids.add(execution_id)
        dispatch_path = root / "agent_runs" / task_id / f"dispatch-{execution_id}.json"
        if not dispatch_path.exists():
            errors.append(f"{task_id} missing dispatch record for {execution_id}")
        else:
            dispatch = load_json(dispatch_path)
            if dispatch.get("status") != "CONSUMED":
                errors.append(f"{task_id} dispatch {execution_id} was not consumed")
            if dispatch.get("dispatch_sha256") != receipt.get("dispatch_sha256"):
                errors.append(f"{task_id} receipt/dispatch hash mismatch")
        run_files = sorted((root / "agent_runs" / task_id).glob("run-*.json"))
        matching = []
        for run_path in run_files:
            env = load_json(run_path)
            if env.get("execution_binding", {}).get("execution_id") == execution_id:
                matching.append((run_path, env))
        if len(matching) != 1:
            errors.append(f"{task_id} must have one envelope bound to {execution_id}, found {len(matching)}")
            continue
        run_path, env = matching[0]
        manifest = env.get("execution_manifest")
        if not isinstance(manifest, dict) or manifest.get("sibling_lens_outputs_present") is not False:
            errors.append(f"{task_id} envelope lacks executable sibling-Lens exclusion proof")
        if not env.get("input_hashes"):
            errors.append(f"{task_id} envelope has no complete input hash manifest")
        payload = env.get("result", {})
        expected_output = result_payload_sha256(payload)
        if receipt.get("output_sha256") != expected_output:
            errors.append(f"{task_id} receipt output hash mismatch")
    return errors


def firewall_errors(root, intent, state):
    errors = []
    if intent not in ("PAPER_READING", "PAPER_TECHNICAL_EXTRACTION"):
        return [f"intent isolation: {intent!r} cannot release a Paper Reader"]
    forbidden = INTENT_INPUT_BOUNDARIES[intent]["forbidden_inputs"]
    allowed_roots = tuple(INTENT_INPUT_BOUNDARIES[intent]["allowed_inputs"] + ["council/", "source_pages/"])

    def inspect_path(value, label):
        text = str(value).replace("\\", "/")
        candidate = Path(text)
        if candidate.is_absolute():
            try:
                text = str(candidate.resolve().relative_to(root.resolve()))
            except ValueError:
                errors.append(f"input firewall: {label} reads outside paper workspace: {value}")
                return
        if ".." in Path(text).parts or any(f.rstrip("/") in Path(text).parts for f in forbidden):
            errors.append(f"input firewall: {label} references forbidden project path: {value}")
            return
        if not (text + "/").startswith(allowed_roots):
            errors.append(f"input firewall: {label} is outside declared paper input roots: {value}")
        resolved = (root / text).resolve()
        if not resolved.is_relative_to(root.resolve()):
            errors.append(f"input firewall: {label} symlink escapes paper workspace: {value}")

    for value in state.get("allowed_inputs", []):
        inspect_path(value, "run_state allowed_inputs")
    for path in sorted((root / "tasks").rglob("*.json")):
        task = load_json(path)
        if task.get("intent") in ("PROJECT_APPLY", "MEMORY_OPERATION"):
            errors.append(f"input firewall: non-reading task present during Paper Reading: {path.relative_to(root)}")
        ok, reason = enforce_task_firewall(task, intent)
        if not ok:
            errors.append(f"input firewall: {reason}")
        for value in task.get("allowed_inputs", []):
            inspect_path(value, f"{path.name} allowed_inputs")
        for value in (task.get("input_artifacts") or {}).values():
            if isinstance(value, str):
                inspect_path(value, f"{path.name} input_artifacts")
    for path in sorted((root / "agent_runs").rglob("*.json")):
        run = load_json(path)
        envelope = run.get("envelope", run)
        for value in (envelope.get("input_hashes") or {}):
            # Some trusted host envelopes record provenance hashes alongside
            # path-to-hash bindings.  Hash field names are metadata, not file
            # paths, and must not trip the paper-input firewall.
            if str(value).endswith("_sha256") or str(value) in {"contract_version", "prompt_version"}:
                continue
            inspect_path(value, f"{path.name} recorded input_hashes")
        for value in envelope.get("accessed_paths", []):
            inspect_path(value, f"{path.name} recorded accesses")
    for forbidden_path in ("apply", "project", "memory/project"):
        if (root / forbidden_path).exists():
            errors.append(f"intent isolation: {forbidden_path}/ exists during {intent}")
    return errors
