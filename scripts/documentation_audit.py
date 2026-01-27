import os
import re
import time
from pathlib import Path
from difflib import SequenceMatcher

from playwright.sync_api import sync_playwright

DOCS_DIR = Path("/Users/jamesmcintosh/Desktop/mrm_inv_3/docs")
BASE_URL = os.environ.get("AUDIT_BASE_URL", "http://localhost:5174")

# Output to project root (parent of scripts dir)
PROJECT_ROOT = Path(__file__).parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "audit_artifacts"
REPORT_PATH = PROJECT_ROOT / "audit_results.md"


class LoginFailedError(RuntimeError):
    pass


WORKFLOW_ALIASES = {
    "model onboarding": ["add model", "create new model", "create model", "new model"],
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _dedupe_keep_order(items):
    seen = set()
    result = []
    for item in items:
        key = _normalize_text(item)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item.strip())
    return result


def _read_pdf_text(path: Path) -> str:
    try:
        import pdfplumber
    except Exception as exc:
        raise RuntimeError(
            "pdfplumber is required for PDF extraction. Install with: pip install pdfplumber"
        ) from exc

    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _extract_inline_items(line: str):
    if ":" not in line:
        return []
    head, rest = line.split(":", 1)
    if "expected workflows" in head.lower() or "required fields" in head.lower():
        items = [item.strip() for item in rest.split(",") if item.strip()]
        return items
    return []


def _parse_text_for_requirements(text: str):
    expected_workflows = []
    required_fields = []
    mode = None

    def _table_first_cell(line_value: str) -> str:
        if not line_value.strip().startswith("|"):
            return ""
        parts = [part.strip() for part in line_value.strip().split("|")]
        cells = [cell for cell in parts if cell]
        if not cells:
            return ""
        first = cells[0]
        if re.fullmatch(r":?-{3,}:?", first):
            return ""
        first = re.sub(r"[*`]", "", first).strip()
        return first

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        inline_items = _extract_inline_items(line)
        if inline_items:
            if "expected workflows" in line.lower():
                expected_workflows.extend(inline_items)
            elif "required fields" in line.lower():
                required_fields.extend(inline_items)
            continue

        lower = line.lower()
        if "expected workflows" in lower:
            mode = "expected"
            continue
        if "required fields" in lower:
            mode = "required"
            continue

        if line.startswith("#"):
            mode = None
            continue

        if mode == "expected":
            item = _table_first_cell(line) or line
            item = re.sub(r"^[-*]\s+", "", item)
            item = re.sub(r"^\d+[\).\s]+", "", item)
            if 2 <= len(item) <= 160:
                expected_workflows.append(item)
        elif mode == "required":
            item = _table_first_cell(line) or line
            item = re.sub(r"^[-*]\s+", "", item)
            item = re.sub(r"^\d+[\).\s]+", "", item)
            if 2 <= len(item) <= 160:
                required_fields.append(item)

    return expected_workflows, required_fields


def load_document_requirements():
    expected_workflows = []
    required_fields = []

    for path in DOCS_DIR.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".md", ".markdown", ".pdf"}:
            continue

        if suffix in {".md", ".markdown"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
        else:
            text = _read_pdf_text(path)

        workflows, fields = _parse_text_for_requirements(text)
        expected_workflows.extend(workflows)
        required_fields.extend(fields)

    return {
        "expected_workflows": _dedupe_keep_order(expected_workflows),
        "required_fields": _dedupe_keep_order(required_fields),
    }


def _ensure_artifacts_dir():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip())
    return value.strip("-").lower() or "item"


def _stabilize_page(page, wait_ms: int = 500):
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(wait_ms)
    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(wait_ms)
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(200)


def _screenshot(page, name: str, counter: int):
    _ensure_artifacts_dir()
    _stabilize_page(page)
    filename = f"{counter:03d}_{_slugify(name)}.png"
    path = ARTIFACTS_DIR / filename
    page.screenshot(path=str(path), full_page=True)
    return f"./{path.as_posix()}"


def _get_accessible_name(locator) -> str:
    return locator.evaluate(
        """
        el => {
          const aria = el.getAttribute('aria-label') || '';
          const labelledBy = el.getAttribute('aria-labelledby');
          let labelText = '';
          if (labelledBy) {
            labelText = labelledBy.split(/\\s+/).map(id => {
              const ref = document.getElementById(id);
              return ref ? ref.innerText : '';
            }).join(' ').trim();
          }
          if (el.labels && el.labels.length) {
            labelText = Array.from(el.labels).map(l => l.innerText).join(' ').trim();
          }
          const placeholder = el.getAttribute('placeholder') || '';
          return [aria, labelText, placeholder].filter(Boolean).join(' ').trim();
        }
        """
    )


def _collect_live_map(page):
    live_map = set()
    text_roles = ["heading", "link", "button",
                  "tab", "menuitem", "option", "listitem"]
    for role in text_roles:
        locator = page.get_by_role(role)
        for text in locator.all_inner_texts():
            if text.strip():
                live_map.add(text.strip())

    form_roles = ["textbox", "combobox", "checkbox", "radio", "spinbutton"]
    for role in form_roles:
        locator = page.get_by_role(role)
        for i in range(locator.count()):
            name = _get_accessible_name(locator.nth(i))
            if name:
                live_map.add(name)

    return live_map


def _fill_first(page, role: str, pattern: re.Pattern, value: str) -> bool:
    locator = page.get_by_role(role, name=pattern)
    if locator.count() == 0:
        return False
    locator.first.fill(value)
    return True


def _click_first(page, role: str, pattern: re.Pattern) -> bool:
    locator = page.get_by_role(role, name=pattern)
    if locator.count() == 0:
        return False
    locator.first.click()
    return True


def _open_login_form(page, screenshot_counter):
    login_trigger = re.compile("log in|login|sign in", re.I)
    clicked = False
    if _click_first(page, "button", login_trigger):
        clicked = True
    elif _click_first(page, "link", login_trigger):
        clicked = True

    if clicked:
        page.wait_for_load_state("networkidle")
        evidence = _screenshot(page, "login_opened", screenshot_counter)
        return evidence, screenshot_counter + 1

    return "", screenshot_counter


def _wait_for_logged_in(page, timeout_ms: int = 10000) -> bool:
    start = time.time()
    dashboard_link = page.get_by_role(
        "link", name=re.compile("dashboard|home", re.I))
    dashboard_heading = page.get_by_role(
        "heading", name=re.compile("dashboard|home", re.I))

    while (time.time() - start) * 1000 < timeout_ms:
        if dashboard_link.count() > 0 or dashboard_heading.count() > 0:
            return True
        page.wait_for_timeout(250)

    return False


def _update_evidence_map(live_items, evidence_map, screenshot_path):
    for item in live_items:
        key = _normalize_text(item)
        if key and key not in evidence_map:
            evidence_map[key] = screenshot_path


def _discover_navigation(page, screenshot_counter):
    live_map = set()
    evidence_map = {}
    nav = page.get_by_role("navigation")
    link_locator = nav.get_by_role("link")

    link_names = []
    for i in range(link_locator.count()):
        name = link_locator.nth(i).inner_text().strip()
        if not name:
            aria = link_locator.nth(i).get_attribute("aria-label")
            if aria:
                name = aria.strip()
        if name:
            link_names.append(name)

    nav_home_evidence = _screenshot(
        page, "navigation_home", screenshot_counter)
    page_items = _collect_live_map(page)
    live_map.update(page_items)
    _update_evidence_map(page_items, evidence_map, nav_home_evidence)
    screenshot_counter += 1

    for name in link_names:
        link = nav.get_by_role("link", name=re.compile(re.escape(name), re.I))
        if link.count() == 0:
            continue
        link.first.click()
        page.wait_for_load_state("networkidle")
        evidence = _screenshot(page, f"nav_{name}", screenshot_counter)
        screenshot_counter += 1
        page_items = _collect_live_map(page)
        live_map.update(page_items)
        _update_evidence_map(page_items, evidence_map, evidence)

    return live_map, evidence_map, nav_home_evidence, screenshot_counter


def _find_alias_match(expected_norm: str, live_items):
    aliases = WORKFLOW_ALIASES.get(expected_norm, [])
    if not aliases:
        return ""
    for item in live_items:
        item_norm = _normalize_text(item)
        for alias in aliases:
            if alias in item_norm:
                return item
    return ""


def _match_expected_item(expected: str, live_items, evidence_map, fallback_evidence):
    expected_norm = _normalize_text(expected)
    if not expected_norm:
        return "MISSING", "", fallback_evidence

    live_norm_map = {_normalize_text(item): item for item in live_items}

    if expected_norm in live_norm_map:
        return "MATCHED", live_norm_map[expected_norm], evidence_map.get(expected_norm, fallback_evidence)

    alias_match = _find_alias_match(expected_norm, live_items)
    if alias_match:
        alias_norm = _normalize_text(alias_match)
        return "MISALIGNED", alias_match, evidence_map.get(alias_norm, fallback_evidence)

    best_item = ""
    best_score = 0.0
    for item in live_items:
        score = SequenceMatcher(None, expected_norm,
                                _normalize_text(item)).ratio()
        if score > best_score:
            best_score = score
            best_item = item

    if best_score >= 0.6:
        best_norm = _normalize_text(best_item)
        return "MISALIGNED", best_item, evidence_map.get(best_norm, fallback_evidence)

    return "MISSING", "", fallback_evidence


def _open_model_onboarding_form(page, screenshot_counter):
    evidence = {"models_page": "", "form_opened": ""}

    models_link = page.get_by_role("link", name=re.compile(r"^models$", re.I))
    if models_link.count() == 0:
        models_link = page.get_by_role("link", name=re.compile("models", re.I))

    if models_link.count() > 0:
        models_link.first.click()
        page.wait_for_load_state("networkidle")
        evidence["models_page"] = _screenshot(
            page, "models_page", screenshot_counter)
        screenshot_counter += 1
    else:
        models_url = f"{BASE_URL}/models"
        page.goto(models_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        evidence["models_page"] = _screenshot(
            page, "models_page", screenshot_counter)
        screenshot_counter += 1

    add_button = page.get_by_role("button", name=re.compile(
        "add model|create new model|new model", re.I))
    if add_button.count() == 0:
        return False, evidence, screenshot_counter

    add_button.first.click()
    page.wait_for_load_state("networkidle")
    model_name_field = page.get_by_role(
        "textbox", name=re.compile("model name", re.I))
    if model_name_field.count() > 0:
        try:
            model_name_field.first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

    evidence["form_opened"] = _screenshot(
        page, "model_onboarding", screenshot_counter)
    screenshot_counter += 1

    return True, evidence, screenshot_counter


def _collect_form_field_names(page):
    names = []
    form_roles = ["textbox", "combobox", "checkbox", "radio", "spinbutton"]
    for role in form_roles:
        locator = page.get_by_role(role)
        for i in range(locator.count()):
            name = _get_accessible_name(locator.nth(i))
            if name:
                names.append(name)
    return names


def _locate_field(page, field_name: str):
    form_roles = ["textbox", "combobox", "spinbutton", "checkbox", "radio"]
    exact = re.compile(rf"^{re.escape(field_name)}$", re.I)
    partial = re.compile(re.escape(field_name), re.I)

    for role in form_roles:
        locator = page.get_by_role(role, name=exact)
        if locator.count() > 0:
            return locator.first, role, "MATCHED"

    for role in form_roles:
        locator = page.get_by_role(role, name=partial)
        if locator.count() > 0:
            return locator.first, role, "MISALIGNED"

    return None, "", "MISSING"


def _preferred_combobox_keywords(field_name: str):
    name = _normalize_text(field_name)
    keywords = []

    if "risk rating" in name or "risk level" in name or "risk severity" in name:
        keywords.extend(["high", "medium", "low"])
    if "model type" in name or "model category" in name:
        keywords.extend(["credit", "market", "operational",
                        "liquidity", "compliance"])
    if "rating" in name and not keywords:
        keywords.extend(["high", "medium", "low"])
    if "tier" in name:
        keywords.extend(["tier 1", "tier 2", "tier 3"])
    if "status" in name:
        keywords.extend(["active", "pending", "inactive"])

    if not keywords:
        keywords.extend(
            ["high", "medium", "low", "credit", "market", "operational"])

    return keywords


def _select_combobox_option(locator, field_name: str):
    locator.click()
    options = locator.page.get_by_role("option")
    option_entries = []
    for i in range(options.count()):
        text = options.nth(i).inner_text().strip()
        if text:
            option_entries.append((text, options.nth(i)))

    keywords = _preferred_combobox_keywords(field_name)
    for keyword in keywords:
        for text, option in option_entries:
            if keyword in _normalize_text(text):
                option.click()
                return True

    if option_entries:
        option_entries[0][1].click()
        return True

    return False


def _fill_field(locator, role: str, field_name: str):
    if role in {"textbox", "spinbutton"}:
        locator.fill("Test Value")
        return
    if role == "combobox":
        _select_combobox_option(locator, field_name)
        return
    if role in {"checkbox", "radio"}:
        locator.check()
        return


def _write_missing_field_html(page, field_name: str):
    _ensure_artifacts_dir()
    filename = f"missing_{_slugify(field_name)}.html"
    path = ARTIFACTS_DIR / filename
    path.write_text(page.content(), encoding="utf-8")


def _write_report(results):
    lines = [
        "# Documentation Audit Results",
        "",
        "## Expected Workflows",
    ]

    for item in results["expected_workflows"]:
        status = results["expected_workflows"][item]["status"]
        note = results["expected_workflows"][item].get("note", "")
        evidence = results["expected_workflows"][item].get("evidence", "")
        if note:
            lines.append(
                f"- [{status}] {item} (UI: {note}) [View Evidence]({evidence})")
        else:
            lines.append(f"- [{status}] {item} [View Evidence]({evidence})")

    lines.extend(["", "## Required Fields (Model Onboarding)"])

    for item in results["required_fields"]:
        status = results["required_fields"][item]["status"]
        note = results["required_fields"][item].get("note", "")
        evidence = results["required_fields"][item].get("evidence", "")
        if note:
            lines.append(
                f"- [{status}] {item} (UI: {note}) [View Evidence]({evidence})")
        else:
            lines.append(f"- [{status}] {item} [View Evidence]({evidence})")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_audit():
    requirements = load_document_requirements()
    expected_workflows = requirements["expected_workflows"]
    required_fields = requirements["required_fields"]

    results = {
        "expected_workflows": {item: {"status": "MISSING"} for item in expected_workflows},
        "required_fields": {item: {"status": "MISSING"} for item in required_fields},
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()
        screenshot_counter = 1

        page.goto(BASE_URL, wait_until="domcontentloaded")
        login_evidence = _screenshot(page, "login_page", screenshot_counter)
        screenshot_counter += 1

        login_opened_evidence, screenshot_counter = _open_login_form(
            page, screenshot_counter)

        _fill_first(page, "textbox", re.compile(
            "user|email|username", re.I), "admin@example.com")
        _fill_first(page, "textbox", re.compile("pass", re.I), "user123")
        if not _click_first(page, "button", re.compile("log in|login|sign in", re.I)):
            page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle")
        post_login_evidence = _screenshot(
            page, "post_login", screenshot_counter)
        screenshot_counter += 1

        if not _wait_for_logged_in(page):
            failure_evidence = _screenshot(
                page, "login_failed", screenshot_counter)
            screenshot_counter += 1
            browser.close()
            raise LoginFailedError(
                f"Login failed. Evidence: {failure_evidence} (initial: {login_evidence}, post-click: {post_login_evidence})"
            )

        live_map, evidence_map, nav_home_evidence, screenshot_counter = _discover_navigation(
            page, screenshot_counter
        )

        form_opened, form_evidence, screenshot_counter = _open_model_onboarding_form(
            page, screenshot_counter
        )
        onboarding_evidence = (
            form_evidence.get("form_opened")
            or form_evidence.get("models_page")
            or nav_home_evidence
        )

        if form_opened:
            form_items = _collect_live_map(page)
            live_map.update(form_items)
            _update_evidence_map(form_items, evidence_map, onboarding_evidence)

            live_fields = _collect_form_field_names(page)
            live_norm_map = {_normalize_text(
                item): item for item in live_fields}

            for field in required_fields:
                locator, role, status = _locate_field(page, field)
                results["required_fields"][field]["evidence"] = onboarding_evidence
                if status == "MATCHED":
                    results["required_fields"][field]["status"] = "MATCHED"
                elif status == "MISALIGNED":
                    results["required_fields"][field]["status"] = "MISALIGNED"
                else:
                    results["required_fields"][field]["status"] = "MISSING"

                if status == "MISSING":
                    _write_missing_field_html(page, field)
                else:
                    _fill_field(locator, role, field)
                    page.wait_for_timeout(200)

                if status == "MISALIGNED":
                    note = live_norm_map.get(_normalize_text(field))
                    if not note:
                        note = _get_accessible_name(locator) if locator else ""
                    if note:
                        results["required_fields"][field]["note"] = note

            filled_evidence = _screenshot(
                page, "model_onboarding_filled", screenshot_counter)
            screenshot_counter += 1

            for field in required_fields:
                if results["required_fields"][field]["status"] != "MISSING":
                    results["required_fields"][field]["evidence"] = filled_evidence
        else:
            for field in required_fields:
                results["required_fields"][field]["status"] = "MISSING"
                results["required_fields"][field]["evidence"] = onboarding_evidence

        for workflow in expected_workflows:
            status, note, evidence = _match_expected_item(
                workflow, live_map, evidence_map, nav_home_evidence
            )
            results["expected_workflows"][workflow]["status"] = status
            results["expected_workflows"][workflow]["evidence"] = evidence
            if note and status == "MISALIGNED":
                results["expected_workflows"][workflow]["note"] = note

        browser.close()

    _write_report(results)


def test_documentation_audit():
    run_audit()


if __name__ == "__main__":
    run_audit()
