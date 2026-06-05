"""Markdown renderer for the post-build EA documentation deliverable.

Split out from :mod:`ea_docs` so that the orchestrator module stays
under the audit script's per-module LOC ceiling (see
``MODULE_LOC_CEILING`` in ``scripts/audit-plan-v5.py``). Public
surface — :func:`render_markdown` — is unchanged and remains
re-exported from ``ea_docs`` via a thin import alias.

Parallel to :func:`ea_docs_render.render_html_document`: same
:class:`DocContent` input, git-diffable text output. Intended for
agent consumption and side-by-side review in PRs. Section headers
and table column labels are localized via ``content.lang``; code
identifiers (``input`` names, MQL5 types, defaults) are rendered
verbatim.
"""

from __future__ import annotations

from .ea_docs_render import DocContent, section_labels, table_headers


__all__ = ["render_markdown"]


# Severity prefix for take-note callouts in the markdown rendering.
#
# PR-18.3 replaced the original ``ℹ️ / ⚠️ / 🔥`` emoji with plain text
# tags (headless Chrome had no emoji font → tofu in PDF). PR-18.4 then
# split the table by language so the EN markdown gets EN tags — the
# rest of ``render_markdown`` already localizes section headers, note
# bodies and table columns, so the severity tag was the last
# hard-coded Vietnamese string.
_SEVERITY_PREFIX: dict[str, dict[str, str]] = {
    "vi": {
        "info": "[Lưu ý]",
        "warn": "[Cảnh báo]",
        "danger": "[Nguy hiểm]",
    },
    "en": {
        "info": "[Note]",
        "warn": "[Warning]",
        "danger": "[Danger]",
    },
}


def render_markdown(content: DocContent) -> str:
    """Render ``DocContent`` as Markdown.

    Parallel to :func:`ea_docs_render.render_html_document` — same
    data, git-diffable text format. Intended for agent consumption
    and side-by-side review in PRs. Section headers and table column
    labels are localized via ``content.lang``; code identifiers
    (``input`` names, MQL5 types, defaults) are rendered verbatim.
    """
    labels = section_labels(content.lang)
    th = table_headers(content.lang)
    lines: list[str] = []
    lines.append("---")
    for k, v in content.frontmatter.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {content.title_main}")
    if content.title_jp:
        # PR-18.3: render the subtitle as plain italics. The legacy
        # `「 」` brackets were dropped because Chrome headless
        # rendered them as tofu squares in the PDF export.
        lines.append(f"_{content.title_jp}_")
    if content.title_en:
        lines.append(f"_{content.title_en}_")
    lines.append("")

    _emit_overview(lines, content, labels)
    _emit_strategy_timeline(lines, content, labels)
    _emit_params_table(lines, content, labels, th)
    _emit_param_deep_dive(lines, content, labels)
    _emit_flow_narrative(lines, content, labels)
    _emit_notes(lines, content, labels)

    return "\n".join(lines).rstrip() + "\n"


def _emit_overview(
    lines: list[str], content: DocContent, labels: dict[str, str]
) -> None:
    if not content.overview_layers:
        return
    lines.append(f"## {labels['overview']}")
    lines.append("")
    for layer in content.overview_layers:
        lines.append(f"- **{layer.title}** — {layer.caption}")
    lines.append("")


def _emit_strategy_timeline(
    lines: list[str], content: DocContent, labels: dict[str, str]
) -> None:
    if not content.strategy_timeline:
        return
    lines.append(f"## {labels['strategy']}")
    lines.append("")
    flow = " → ".join(
        f"**{s.label}**" if s.highlight else s.label
        for s in content.strategy_timeline
    )
    lines.append(flow)
    lines.append("")
    for step in content.strategy_timeline:
        if step.caption:
            lines.append(f"- _{step.label}_: {step.caption}")
    lines.append("")


def _emit_params_table(
    lines: list[str],
    content: DocContent,
    labels: dict[str, str],
    th: tuple[str, str, str, str, str],
) -> None:
    if not content.params:
        return
    lines.append(f"## {labels['params']}")
    lines.append("")
    lines.append(f"| {th[0]} | {th[1]} | {th[2]} | {th[3]} | {th[4]} |")
    lines.append("|---|---|---|---|---|")
    for p in content.params:
        note = (p.note or "").replace("|", "\\|")
        lines.append(
            f"| {p.group or '-'} | `{p.name}` | `{p.type}` | "
            f"`{p.default}` | {note} |"
        )
    lines.append("")


def _emit_param_deep_dive(
    lines: list[str], content: DocContent, labels: dict[str, str]
) -> None:
    if not content.enriched_params:
        return
    lines.append(f"## {labels['param_deep_dive']}")
    lines.append("")
    no_doc = (
        "Chưa có mô tả trong input-semantics.yaml."
        if content.lang == "vi"
        else "Not yet documented in input-semantics.yaml."
    )
    dd_labels = (
        ("Ý nghĩa", "Đơn vị", "Công thức", "Phụ thuộc",
         "Sử dụng bởi", "Dải hợp lý", "Lưu ý")
        if content.lang == "vi"
        else ("Meaning", "Unit", "Formula", "Depends on",
              "Used by", "Sensible range", "Gotchas")
    )
    dd_default_label = "mặc định" if content.lang == "vi" else "default"
    dd_group_label = "nhóm" if content.lang == "vi" else "group"
    for row in content.enriched_params:
        header_bits = [
            f"`{row.name}` (`{row.type}`, {dd_default_label} `{row.default}`)"
        ]
        if getattr(row, "group", ""):
            header_bits.append(f"_{dd_group_label}: {row.group}_")
        lines.append(f"### {' — '.join(header_bits)}")
        lines.append("")
        sem = getattr(row, "semantic", None)
        if sem is None:
            tooltip = (row.tooltip or "").strip()
            if tooltip:
                lines.append(tooltip)
                lines.append("")
            lines.append(f"_{no_doc}_")
            lines.append("")
            continue

        def _row(label: str, value: str) -> None:
            if value:
                lines.append(f"- **{label}:** {value}")

        _row(dd_labels[0], sem.meaning)
        _row(dd_labels[1], sem.unit)
        _row(dd_labels[2], sem.formula)
        if sem.depends_on:
            _row(dd_labels[3], ", ".join(f"`{d}`" for d in sem.depends_on))
        _row(dd_labels[4], sem.used_by)
        _row(dd_labels[5], sem.sensible_range)
        _row(dd_labels[6], sem.gotchas)
        lines.append("")


def _emit_flow_narrative(
    lines: list[str], content: DocContent, labels: dict[str, str]
) -> None:
    if not content.flow_narrative:
        return
    lines.append(f"## {labels['flow']}")
    lines.append("")
    lines.append(content.flow_narrative.rstrip())
    lines.append("")


def _emit_notes(
    lines: list[str], content: DocContent, labels: dict[str, str]
) -> None:
    if not content.notes:
        return
    lines.append(f"## {labels['notes']}")
    lines.append("")
    # PR-18.3: severity prefixes use plain text labels instead of
    # emoji. The previous ``ℹ️ / ⚠️ / 🔥`` emoji rendered as tofu
    # squares in headless-Chrome PDF export (no emoji font
    # installed). Text labels render correctly in any font.
    sev_prefix = _SEVERITY_PREFIX.get(content.lang, _SEVERITY_PREFIX["vi"])
    default_prefix = sev_prefix["info"]
    for n in content.notes:
        prefix = sev_prefix.get(n.severity, default_prefix)
        lines.append(f"> {prefix} **{n.title}**")
        lines.append(f"> {n.body}")
        lines.append("")
