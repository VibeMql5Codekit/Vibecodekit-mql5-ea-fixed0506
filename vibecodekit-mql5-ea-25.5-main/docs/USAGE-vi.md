---
id: usage-vi
title: Hướng dẫn sử dụng vibecodekit-mql5-ea v1.6.1 (Tiếng Việt)
applicable_phase: E
audience: end_user, dev_team
---

# Hướng dẫn sử dụng `vibecodekit-mql5-ea` v1.6.1

Tài liệu này hướng dẫn từng bước cách dùng toàn bộ **69 lệnh CLI**
(59 lệnh độc lập + 10 alias Wave-3 quy về 2 umbrella `mql5-review --lens`
và `mql5-rri <subcommand>`; bao gồm 3 generator Wave-5.1 `mql5-vision-gen` /
`mql5-blueprint-gen` / `mql5-tip-gen` và các emitter Wave-6.1 / 6.2 / 6.2b)
để build một Expert Advisor MQL5
hoàn chỉnh, từ ý tưởng đến ship live. Phù hợp cho cả người mới, dev team
và LLM agent (Devin, Claude Code, Cursor, ChatGPT).

Baseline hiện tại: **`v1.6.1`**, **1494 test passing / 4 skipped** (1499 collected; 1 probe MetaEditor compile cần Wine), **26 anti-pattern
detector** (25 đánh số AP-1…AP-25 + 1 method-hiding theo build), **4 MCP
server**, **23 scaffold archetype**,
**8 schema block optional** trên `ea-spec.yaml`.

> 📚 Phiên bản tiếng Anh: [USAGE-en.md](USAGE-en.md)
> 🛠️ Tích hợp IDE / CLI (Devin, Codex, Claude Code, Cursor, …): [ENV-SETUP-vi.md](ENV-SETUP-vi.md)
> 💬 Build theo prompt (chat → spec → pipeline): [devin-chat-driven-build.md](devin-chat-driven-build.md)

## Mục lục

1. [Cài đặt môi trường](#1-cài-đặt-môi-trường)
2. [Triết lý: 8 bước build EA](#2-triết-lý-8-bước-build-ea)
3. [Lệnh theo từng giai đoạn](#3-lệnh-theo-từng-giai-đoạn)
4. [Ví dụ hoàn chỉnh: MACD+SAR EURUSD H1](#4-ví-dụ-hoàn-chỉnh-macdsar-eurusd-h1)
5. [Tích hợp 4 MCP server](#5-tích-hợp-4-mcp-server)
6. [26 anti-pattern detector](#6-26-anti-pattern-detector)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Cài đặt môi trường

### 1.1. Yêu cầu

| Thành phần | Phiên bản |
|-----------|-----------|
| Python | ≥ 3.10 |
| Wine | 8.0.2 (Linux/macOS) — MetaEditor là native trên Windows |
| MetaEditor | build ≥ 5260 (để method-hiding linter ở mức ERROR thay vì WARN) |
| ONNX runtime | 1.14 (ONNX e2e cho ml-onnx scaffold + `mql5-onnx-export` / `mql5-onnx-embed`) |
| Xvfb | tuỳ — cần nếu chạy headless trên CI Linux |

### 1.2. Linux (Ubuntu 22.04+)

```bash
git clone https://github.com/VibeMql5Codekit/vibecodekit-mql5-ea-25.5
cd vibecodekit-mql5-ea-25.5

# Cài Wine + MetaEditor headless qua wineboot (~3 phút)
./scripts/setup-wine-metaeditor.sh

# Tạo venv riêng cho kit
python -m venv .venv
source .venv/bin/activate

# Cài kit (pyyaml auto-pull; thêm [dev] cho pytest + ruff)
pip install -e .[dev]

# Health check — mọi probe phải là ok: true
python -m vibecodekit_mql5.doctor

# Không có Wine? Dùng soft mode (chỉ relax probe môi trường,
# vẫn check Python + scaffolds + manifest):
python -m vibecodekit_mql5.doctor --soft
```

Kit chạy đầy đủ trên Linux **không cần Wine** cho mọi tác vụ
lint / docs / unit test / Wave-5 generator / sentinel validator /
`mql5-bt-sim` (in-process tick-bar simulator) / `mql5-forge-loop`
(hermetic). Wine + MetaEditor chỉ cần khi muốn compile `.mq5` →
`.ex5` thật và chạy Strategy Tester end-to-end.

### 1.3. macOS

Wine trên macOS chạy được nhưng MetaQuotes không support chính thức.
Khuyến nghị dùng Devin VM hoặc Linux VM. Nếu vẫn muốn local:

```bash
brew install --cask wine-stable
# Sau đó các bước giống Linux
```

### 1.4. Windows

MetaEditor là native nên không cần Wine. Dùng PowerShell:

```powershell
git clone https://github.com/VibeMql5Codekit/vibecodekit-mql5-ea-25.5
cd vibecodekit-mql5-ea-25.5
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python -m vibecodekit_mql5.doctor
```

> ⚠️ Một số script `setup-wine-metaeditor.sh` là bash-only — trên Windows
> chỉ cần chỉ định path MetaEditor qua env var `METAEDITOR_BIN` rồi bỏ
> qua bước Wine.

---

## 2. Triết lý: 8 bước build EA

Plan v5 chia toàn bộ vòng đời EA thành 8 bước. Mỗi bước có template
markdown trong `docs/rri-templates/` và lệnh chuyên dụng để mở nó:

| Bước | Tên | Lệnh mở template (renderer) | Lệnh auto-gen (Wave 5.1) | Output |
|------|-----|------------------------------|---------------------------|--------|
| 1 | **SCAN** | `python -m vibecodekit_mql5.scan <thư mục>` | — | Liệt kê tree project |
| 2 | **RRI** (Research / Risk / Robustness) | `python -m vibecodekit_mql5.rri --mode {personal,team,enterprise}` | — | `docs/rri-report.md` (25 câu × 6 persona) |
| 3 | **VISION** | `python -m vibecodekit_mql5.vision` | `mql5-vision-gen <step-2-rri.md>` | `step-3-vision.md` |
| 4 | **BLUEPRINT** | `python -m vibecodekit_mql5.blueprint` | `mql5-blueprint-gen <ea-spec.yaml> [--vision <step-3-vision.md>]` | `step-4-blueprint.md` (18 preset-keyed invariant + module diagram + state machine) |
| 5 | **TIP** (Technical Implementation Plan) | `python -m vibecodekit_mql5.tip` | `mql5-tip-gen <step-4-blueprint.md>` | `step-5-tip.md` (bảng module × test pytest-compatible) |
| 6 | **BUILD** | `python -m vibecodekit_mql5.build <archetype>` hoặc `wizard`, `async-build` | — | Mã `.mq5` từ scaffold |
| 7 | **VERIFY** | 10 lệnh từ `compile` → `multibroker` | — | XML report + ma trận 64 ô |
| 8 | **REFINE + SHIP** | `python -m vibecodekit_mql5.refine` + `ship` | — | Tag git + push |

**Wave 5.1 generator** (`mql5-vision-gen` / `mql5-blueprint-gen` /
`mql5-tip-gen`) emit `step-3..5-*.md` deterministic từ artefact của
step trước. Không gọi LLM, không hardcode per-archetype. Skeleton sau
khi sinh ra cần một LLM agent (paste prompt từ `docs/agent-prompts/`,
xem §3.13) tinh chỉnh narrative.

**Wave 5.2 sentinel-content validator** đảm bảo từng step output có
đủ checkbox `## Activities` tick (`personal ≥ 50%` / `team ≥ 80%` /
`enterprise = 100%`) trước khi gate Layer 5 cho qua — xem §3.9
(`mql5-permission --layer5-enforce-activities`).

**Wave 5.3 — 6 persona prompt paste-and-run** dưới `docs/agent-prompts/`
biến mọi LLM chat ngoài (Claude, ChatGPT, Cursor, Devin) thành một
trong các vai: `strategy-architect` (quant), `broker-engineer` (kỹ sư
MQL5), `risk-auditor` (compliance), `devops`, `perf-analyst`,
`trader` (chủ nhà / end-user) — xem §3.13.

### Phân loại 3 mode

| Mode | Số câu RRI | Lớp permission chạy | Đối tượng |
|------|----------|---------------------|----------|
| `personal` | 5 q/persona × 6 = 30 | 1, 2, 3, 4, 7 | Solo trader |
| `team` | 12 q/persona × 6 = 72 | 1-5, 7 | Team 2-5 dev |
| `enterprise` | 25 q/persona × 6 = 150 | 1-7 (đầy đủ) | Tổ chức / quỹ |

---

## 3. Lệnh theo từng giai đoạn

### 3.1. Discovery (4 lệnh)

```bash
# Quét cây thư mục project, phân loại artefact
python -m vibecodekit_mql5.scan ~/projects/eurusd-portfolio

# Match mô tả tự do → scaffold archetype
python -m vibecodekit_mql5.survey "MA cross strategy H1 trend following"
# → primary: trend, variant: netting

# Health check môi trường kit
python -m vibecodekit_mql5.doctor

# Chạy 70-test conformance battery
python -m vibecodekit_mql5.audit
```

### 3.2. Plan — template + Wave-5.1 generators (7 lệnh)

```bash
# Template renderer (mở skeleton)
python -m vibecodekit_mql5.rri --mode team    # mở rri-template + chấm điểm
python -m vibecodekit_mql5.vision             # mở step-3-vision template
python -m vibecodekit_mql5.blueprint          # mở step-4-blueprint
python -m vibecodekit_mql5.tip                # mở step-5-tip

# Wave 5.1 — bộ sinh step-output deterministic (KHÔNG gọi LLM)
mql5-vision-gen step-2-rri.md --out step-3-vision.md
mql5-blueprint-gen ea-spec.yaml --vision step-3-vision.md --out step-4-blueprint.md
mql5-tip-gen step-4-blueprint.md --out step-5-tip.md
```

`mql5-vision-gen` parse Step-2 RRI cho `## Constraints` + dòng
`- [x] persona::q-id`, điền Scope / Active personas vào
`step-3-vision.md`. Timeline + Risk register giữ là `TODO` cho operator
(hoặc LLM persona phía sau) refine.

`mql5-blueprint-gen` load `ea-spec.yaml`, validate qua `spec_schema`,
seed bảng invariants Step-4 từ 18 template preset-keyed
(`PRESET_INVARIANTS` trong `step_gen/blueprint_gen.py`). Module diagram
+ state machine được suy ra từ signals / filters / stack / preset
(nhánh sync vs async vs indicator-only). Truyền
`--vision <step-3-vision.md>` để fuse Scope từ step trước.

`mql5-tip-gen` parse `## Invariants` checkbox + fenced block đầu tiên
dưới `## Module diagram` trong BLUEPRINT. Mỗi invariant emit row với
module liên quan nhất (heuristic theo keyword: `CPipNormalizer.mqh` /
`CMagicRegistry.mqh` / `CRiskGuard.mqh` / signal block / filter block)
+ tên test snake_case pytest-compatible `test_<slug>`. Owner test +
interface để TODO cho operator refine.

Cả 3 generator support envelope Wave-1 `--json` + `--gate-report <path>`
chuẩn.

### 3.3. Build (13 lệnh)

```bash
# 1. Render scaffold tổng quát — chọn archetype + variant
python -m vibecodekit_mql5.build stdlib --name MyEA --symbol EURUSD --tf H1
# Archetype có sẵn: stdlib, trend, mean-reversion, breakout, scalping,
# hedging-multi, news-trading, arbitrage-stat, library, indicator-only,
# grid, dca, portfolio-basket, wizard-composable, hft-async, ml-onnx,
# service-llm-bridge

# 2. Wizard composable (CExpert + signal + trailing + money-mgmt)
python -m vibecodekit_mql5.wizard --name MyWizardEA --symbol EURUSD --tf H1

# 3. HFT async — OrderSendAsync + OnTradeTransaction handler
python -m vibecodekit_mql5.async_build --name MyHftEA --symbol EURUSD --tf M1

# 4. Patch EA hiện có dùng CPipNormalizer
python -m vibecodekit_mql5.pip_normalize MyEA.mq5

# 5. Export PyTorch / TF → ONNX (opset ≥ 14)
python -m vibecodekit_mql5.onnx_export model.pt --output model.onnx --opset 14

# 6. Embed file .onnx vào .mq5 qua #resource + COnnxLoader
python -m vibecodekit_mql5.onnx_embed MyEA.mq5 --model model.onnx

# 7. Wire LLM bridge vào EA hiện có
python -m vibecodekit_mql5.llm_context MyEA.mq5 --pattern cloud-api
# Pattern: cloud-api | self-hosted-ollama | embedded-onnx-llm

# 8. Khởi tạo repo trên Algo Forge
python -m vibecodekit_mql5.forge_init MyEA

# 9. Render docs end-user cho EA đã build (bình thường `mql5-auto-build`
#    gọi tự động; chạy standalone khi muốn refresh docs)
mql5-ea-docs ea-spec.yaml MyEA.mq5 --out build/MyEA --lang vi --formats html,md
```

`mql5-ea-docs` xuất `MyEA.docs.html` + `MyEA.docs.md` (và `.docs.pdf`
khi có headless Chrome). Nội dung gồm:

* **Kiến trúc hệ thống** — sơ đồ 3 lớp Signal / Risk / Execute.
* **Chu trình chiến lược** — timeline 4 bước.
* **Tham số EA** — bảng input tự động parse từ `.mq5`.
* **Chi tiết từng tham số** — card deep-dive per input (ý nghĩa,
  công thức, dải hợp lý, phụ thuộc input khác, pitfall) lấy từ
  `docs/input-semantics.yaml`.
* **Cách EA chạy** — tường thuật OnInit / OnTick (hoặc OnTimer /
  OnStart) / OnDeinit theo archetype, lấy từ
  `scaffolds/<preset>/<stack>/FLOW-vi.md` (hiện mới có tiếng Việt;
  `FLOW-en.md` nằm trong roadmap).
* **Setup khuyến nghị** — bảng tune theo size tài khoản / broker /
  context prop-firm.
* **Ghi chú quan trọng** — cảnh báo rule-driven (PipNormalizer,
  permission gate, AP-17 / AP-18).

Flag: `--lang {vi,en}` (default `vi`), `--formats html,md[,pdf]`,
`--ea-version`, `--compile-status PASS|FAIL`, `--gate-status PASS|FAIL`.

#### 3.3a. Pipeline auto-build 1 lệnh

4 CLI dưới đây lấp khoảng trống giữa "tôi muốn EA làm X" và PR
xanh CI. Mỗi lệnh deterministic, chỉ dùng regex (không gọi LLM), output
JSON hoặc YAML để feed sang stage kế tiếp.

```bash
# Free-text → ea-spec.yaml hợp lệ (--explain để xem field nào suy ra từ
# prompt, field nào lấy default; --strict để fail nếu thiếu).
mql5-spec-from-prompt "build EA trend EURUSD H1 risk 0.5% macd or sar" \
    --out ea-spec.yaml --explain

# Pipeline 1-lệnh: scan → build → lint → compile → permission-gate →
# dashboard. Ghi auto-build-report.json (idempotent).
mql5-auto-build --spec ea-spec.yaml --out-dir build/MyEA

# Áp transformer loop 8 AP nghiêm trọng cho file .mq5 cũ
# (AP-1, 3, 5, 15, 17, 18, 20, 21). Re-lint sau mỗi pass.
mql5-auto-fix MyEA.mq5

# Render + (tuỳ chọn) publish ma trận chất lượng 64 ô ra HTML.
# Đọc MQL5_DASHBOARD_PUBLISH_CMD hoặc --publish-cmd; fallback file://.
mql5-dashboard --metrics metrics.json --out quality-matrix.html
```

Các flag cần nhớ:

* `mql5-auto-build --no-compile` — bỏ qua stage Wine + MetaEditor (hữu ích
  khi CI không có Wine hoặc chỉ muốn chạy lint/gate).
* `mql5-auto-build --no-gate` — bỏ qua orchestrator 7 lớp.
* `mql5-auto-build --force` — render lại scaffold ngay cả khi `out_dir`
  đã có file.
* `mql5-auto-build --publish-cmd <cmd>` — override hook publish
  dashboard cho lần chạy đó.

Schema của `ea-spec.yaml` (risk / signals / filters / hooks / stack
overrides) nằm ở `scripts/vibecodekit_mql5/spec_schema.py`. Bảng
recogniser của `mql5-spec-from-prompt` có ở
[`devin-chat-driven-build.md`](devin-chat-driven-build.md#what-the-parser-understands).

### 3.4. Verify (13 lệnh)

```bash
# 1. Compile qua MetaEditor (Wine trên Linux)
python -m vibecodekit_mql5.compile MyEA.mq5

# 2. Lint 8 anti-pattern nghiêm trọng (ERROR-level, block ship)
python -m vibecodekit_mql5.lint MyEA.mq5

# 2b. Wave 3.D POC — bật AST scanner MQL5 nhẹ cho AP-1 (no SL) /
#     AP-2 (SL quá chặt) / AP-7 (magic hardcode). Các AP code khác
#     vẫn dùng regex. Finding byte-identical so với pipeline regex
#     trên toàn bộ 20 EA + 23 scaffold golden, nên cờ này an toàn
#     để cắm vào CI hiện tại:
mql5-lint MyEA.mq5 --use-ast
mql5-lint MyEA.mq5 --use-ast --json --gate-report gate-report-lint.json

# 3. Method-hiding linter (build ≥ 5260 → ERROR; build < 5260 → WARN)
python -m vibecodekit_mql5.method_hiding_check MyEA.mq5 --build 5260

# 4. Parse Strategy Tester XML report → 14 canonical metrics JSON
#    Chạy MetaEditor backtest tay trước, lưu XML, rồi parse:
python -m vibecodekit_mql5.backtest MyEA.ex5 inputs.set \
    --period H1 --symbol EURUSD --report tester.xml > metrics.json

# 4b. Chạy Strategy Tester end-to-end (drive terminal64.exe qua Wine
#     + parse XML). Cần $MQL5_TERMINAL_PATH (export bởi
#     scripts/setup-wine-metaeditor.sh).
python -m vibecodekit_mql5.tester_run MyEA.ex5 \
    --symbol EURUSD --period H1 --from 2024-01-01 --to 2024-06-01 \
    --out tester.xml > metrics.json

# 4c. Chạy optimization end-to-end (drive terminal64.exe + parse opt XML
#     → top-N parameter set). File .set phải có flag optimize=true kèm
#     start/step/stop; mql5-optimize-run không tự sinh range.
python -m vibecodekit_mql5.optimize_run MyEA.ex5 default.set \
    --symbol EURUSD --period 2024.01.01-2024.12.31 --tf H1 \
    --mode genetic --criterion sharpe-max --top 10 > top-sets.json

# CI / hermetic: parse opt XML có sẵn, không launch MT5
python -m vibecodekit_mql5.optimize_run MyEA.ex5 default.set \
    --period 2024.01.01-2024.12.31 \
    --from-xml /path/to/opt-results.xml --criterion sharpe-max

# 5. Walk-forward IS/OOS (cần 2 XML report đã chạy IS và OOS riêng)
python -m vibecodekit_mql5.walkforward is.xml oos.xml > walkforward.json

# 6. Monte-Carlo bootstrap DD (CSV 1 return / dòng, có header tuỳ chọn)
python -m vibecodekit_mql5.monte_carlo returns.csv \
    --reported-dd 5.4 --n-sims 1000 --seed 42 > montecarlo.json

# 7. Overfit check (Sharpe OOS/IS sanity)
python -m vibecodekit_mql5.overfit_check is.xml oos.xml > overfit.json

# 8. Multi-broker stability (3 XML report tách dấu phẩy)
python -m vibecodekit_mql5.multibroker \
    --reports brokerA.xml,brokerB.xml,brokerC.xml

# 9. Custom fitness emitter (positional; bỏ trống để list 5 template)
python -m vibecodekit_mql5.fitness sharpe > OnTester.mq5

# 10. MFE/MAE per-trade analyser (CSV 8 cột: deal_id,open_time,
#     close_time,magic,type,profit,mfe,mae — emit từ CMfeMaeLogger.mqh)
python -m vibecodekit_mql5.mfe_mae mfe.csv
```

> **Lưu ý:** `mql5-backtest`, `mql5-walkforward`, `mql5-overfit_check`,
> `mql5-multibroker` chỉ **parse** XML report — KHÔNG tự chạy Strategy
> Tester. Bạn vẫn phải chạy backtest qua MetaTrader 5 (hoặc tự automate
> bằng `terminal64.exe /config:tester.ini`), lưu HTML/XML report, rồi
> feed vào các lệnh này. Lệnh `cloud_optimize` chỉ sinh `tester.ini` cho
> bạn copy lên Cloud Network của MetaQuotes.

> **CSV schema cho `mfe_mae`** — cột bắt buộc đúng thứ tự:
> `deal_id,open_time,close_time,magic,type,profit,mfe,mae` (xuất từ
> `CMfeMaeLogger.SaveToCsv()`; xem `Include/CMfeMaeLogger.mqh`).

### 3.5. RRI methodology (4 — 1 umbrella + 3 alias Wave-3)

Wave 3 gộp 3 CLI RRI (`mql5-rri-bt`, `mql5-rri-rr`, `mql5-rri-chart`)
vào 1 umbrella `mql5-rri` với subcommand. 3 console script cũ giữ
nguyên dưới dạng **alias Wave-3** (forward 1-line sang umbrella) —
JSON output byte-identical, có thêm field `data.kind`. **Code mới
dùng umbrella.**

```bash
# Umbrella (nên dùng):
mql5-rri                                            # legacy: in template RRI Bước 2
mql5-rri template                                   # subcommand template tường minh
mql5-rri bt    --metrics metrics.json --mode enterprise --output rri-bt.html
mql5-rri rr    --trader-check tc.json --walkforward wf.json \
               --monte-carlo  mc.json --overfit     of.json \
               --mode enterprise --output rri-rr.html
mql5-rri chart --metrics chart.json --mode personal --output rri-chart.html

# Alias cũ (giữ để back-compat, tương đương subcommand umbrella ở trên):
mql5-rri-bt    --metrics metrics.json --mode enterprise --output rri-bt.html
mql5-rri-rr    --trader-check tc.json --walkforward wf.json \
               --monte-carlo  mc.json --overfit     of.json \
               --mode enterprise --output rri-rr.html
mql5-rri-chart --metrics chart.json --mode personal --output rri-chart.html

# Module-level (chạy cả qua umbrella lẫn alias đều OK):
python -m vibecodekit_mql5.rri bt    --metrics metrics.json --mode enterprise --output rri-bt.html
python -m vibecodekit_mql5.rri.rri_bt    --metrics metrics.json --mode enterprise --output rri-bt.html
python -m vibecodekit_mql5.rri.rri_rr    --trader-check tc.json --walkforward wf.json \
                                         --monte-carlo  mc.json --overfit     of.json \
                                         --mode personal --output rri-rr.html
python -m vibecodekit_mql5.rri.rri_chart --metrics chart.json --mode personal --output rri-chart.html
```

#### Matrix cell-coverage audit (Wave 4.3)

Ma trận RRI 8×8 có 64 cell, nhưng chỉ **6** cell được fill
discriminative bằng artefact `--gate-report` Wave-1 (mỗi cell tương
ứng đúng 1 (dim, axis)). 58 cell còn lại hoặc đến từ RRI HTML review
broadcast cùng dim status cho cả 8 axes (`rri_broadcast`, 50 cell),
hoặc hoàn toàn không có automation (`manual`, 8 cell — toàn bộ hàng
`d_inference`).

Threshold legacy `passes_personal()` / `passes_enterprise()` giả định
**toàn bộ** 64 cell được fill, nên trong thực tế **luôn fail** khi
matrix chỉ được build từ collector W1.4. Dùng **gate-only verdict**
thay thế — chỉ tính 6 cell mà collector thật sự fill được.

```bash
# Audit độc lập — không cần inputs / không cần report:
python -m vibecodekit_mql5.rri.matrix --audit
# In ra:
# {
#   "schema_version": "1",
#   "total_cells": 64,
#   "counts": {"gate_auto": 6, "rri_broadcast": 50, "manual": 8},
#   "cells": { … per-cell map kèm tool gate-report cho mỗi gate_auto cell … }
# }

# Collect → matrix → HTML, envelope thêm gate-only verdict:
python -m vibecodekit_mql5.rri.matrix --collect ./reports/ --output matrix.html
# Envelope thêm field (Wave 4.3):
#   counts_by_coverage:      đếm status theo coverage class
#   passes_personal_gate_only:   verdict PASS theo 6 gate_auto cell
#   passes_enterprise_gate_only: PASS strict (0 WARN) trên cùng 6 cell
```

HTML report giờ phân biệt 3 coverage class bằng border: viền xanh đậm
= `gate_auto`, đường gạch tím = `rri_broadcast`, dotted xám mờ =
`manual` — reviewer thấy ngay cell nào có signal thật sự per-(dim,
axis), cell nào chỉ là filler.

4 trong 6 cell `gate_auto` được fill bởi **nhiều hơn một** emitter
Wave-1 (ví dụ `d_correctness × implement` có 3 tool: `mql5-lint`,
`mql5-method-hiding-check`, `mql5-bt-sim`). Khi nhiều gate-report
cùng đổ về một cell, `--collect` giữ **status xấu nhất**
(`FAIL > WARN > PASS > N/A`) và nối note của mọi tool vào cell-note để
reviewer trace được verdict. Một `FAIL` từ bất kỳ emitter nào sẽ không
bị một `PASS` có tên file alphabetically lớn hơn ghi đè im lặng.

`--audit` bỏ qua `--output` và in JSON ra stdout. Nếu user truyền cả
hai cờ, CLI in cảnh báo stderr và vẫn exit 0.

| Cell                                | Coverage class    | Tool discriminative                                                    |
|-------------------------------------|-------------------|------------------------------------------------------------------------|
| `d_correctness × implement`         | `gate_auto`       | `mql5-lint`, `mql5-method-hiding-check`, `mql5-bt-sim`                 |
| `d_correctness × integration`       | `gate_auto`       | `mql5-permission`                                                      |
| `d_risk × design`                   | `gate_auto`       | `mql5-trader-check`                                                    |
| `d_robustness × backtest`           | `gate_auto`       | `mql5-backtest`, `mql5-monte-carlo`, `mql5-mfe-mae`, `mql5-forge-loop` |
| `d_robustness × walk_forward`       | `gate_auto`       | `mql5-walkforward`, `mql5-overfit-check`                               |
| `d_broker_safety × multi_broker`    | `gate_auto`       | `mql5-broker-safety`, `mql5-multibroker`                               |
| `d_inference × *`  (toàn hàng)      | `manual`          | không có — phải fill qua `--inputs` JSON                               |
| _(50 cell khác)_                    | `rri_broadcast`   | `mql5-rri bt|rr|chart` (broadcast cùng dim status cho cả 8 axes)       |

### 3.6. Review opener (6 — 1 umbrella + 4 alias Wave-3 + 1 standalone)

Wave 3 gộp 4 CLI review-persona (`mql5-eng-review`, `mql5-ceo-review`,
`mql5-cso`, `mql5-investigate`) vào umbrella `mql5-review` qua cờ mới
`--lens <eng|ceo|cso|investigate>`. 4 console script cũ giữ nguyên
dưới dạng **alias Wave-3** (forward 1-line sang `mql5-review --lens
<tên>`); JSON output byte-identical, có thêm `data.lens` + `data.steps`.
**Code mới dùng umbrella.** `mql5-second-opinion` là standalone
fast-pass (lint + Trader-17 trên `.mq5`) — **không** phải lens, không
gộp.

```bash
# Umbrella (nên dùng):
mql5-review                                              # legacy: mở template review base
mql5-review --lens eng         --mode personal --output eng-review.md
mql5-review --lens ceo         --mode personal --output ceo-review.md
mql5-review --lens cso         --mode personal --output cso-review.md
mql5-review --lens investigate --mode personal --output investigate.md
mql5-review --persona trader --step verify --mode personal --output review.md   # single-persona path cũ (giữ nguyên)

# Alias cũ (giữ để back-compat):
mql5-eng-review   --mode personal --output eng-review.md
mql5-ceo-review   --mode personal --output ceo-review.md
mql5-cso          --mode personal --output cso-review.md
mql5-investigate  --mode personal --output investigate.md

# Standalone (KHÔNG phải lens — lint + Trader-17 fast pass trên .mq5):
mql5-second-opinion EA.mq5

# Module-level:
python -m vibecodekit_mql5.review --lens eng --mode personal --output eng-review.md
python -m vibecodekit_mql5.review.eng_review
python -m vibecodekit_mql5.review.ceo_review
python -m vibecodekit_mql5.review.cso
python -m vibecodekit_mql5.review.investigate
```

### 3.7. Deploy (3 lệnh)

```bash
# Sinh checklist MIGRATE-VPS.md cho VPS deployment
python -m vibecodekit_mql5.deploy_vps MyEA --out MIGRATE-VPS.md --mode personal

# Sinh tester.ini cho MetaQuotes Cloud Network optimization
# Mode PERSONAL bị reject (quá đắt); team/enterprise phải có budget cap
python -m vibecodekit_mql5.cloud_optimize MyEA \
    --symbol EURUSD --period H1 --passes 1000 --budget-usd 50 \
    --mode enterprise --output-ini tester.ini

# Canary live monitor 30 phút sau deploy
# Đọc journal MT5 qua mt5-bridge MCP; alert nếu error_rate > 1/min,
# slippage_p95 > 1 pip, hoặc DD > 5%
# (Có thể dùng --journal <file.log> thay vì poll real-time.)
python -m vibecodekit_mql5.canary MyEA.ex5 --duration 30m
```

### 3.8. Ship (4 lệnh)

```bash
# Push PR sang Algo Forge
python -m vibecodekit_mql5.forge_pr feature-branch --target main

# Đóng gói output của mql5-auto-build thành manifest + ship.zip
python -m vibecodekit_mql5.package --out-dir ./dist --spec ea-spec.yaml
# Hoặc bật trực tiếp trong pipeline build (chỉ chạy khi build xanh):
python -m vibecodekit_mql5.auto_build --spec ea-spec.yaml --out-dir ./dist --package

# Git tag + push (dry-run trước cho an toàn)
python -m vibecodekit_mql5.ship --tag v1.0.1 --dry-run
python -m vibecodekit_mql5.ship --tag v1.0.1

# Phân loại diff thành tweak / patch / rework
python -m vibecodekit_mql5.refine --diff change.patch
# Output: { "classification": "tweak", "files_touched": ["set.set"], ... }
```

**Nội dung file ship `.zip`.** `mql5-package` (và
`mql5-auto-build --package`) duyệt `--out-dir`, phân loại file qua
`scripts/vibecodekit_mql5/package.py::classify_artifact`, ghi
`manifest.json` (SHA-256 + group index) rồi đóng gói thành
`<out-dir>/<name>-ship.zip`. Các nhóm trong gói:

| Group     | File                                                                | Mục đích                                                       |
|-----------|---------------------------------------------------------------------|----------------------------------------------------------------|
| `runtime` | `*.ex5`, `Sets/*.set`                                               | Copy vào MT5 để chạy EA / Strategy Tester preset               |
| `source`  | `*.mq5`, `*.mqh`, `README.md` của scaffold                          | Recompile, audit source, review scaffold                       |
| `review`  | `auto-build-report.json`, `quality-matrix.html`, `*.docs.*`, `*.log` | Verdict build / lint / compile / gate + tài liệu EA (`.docs.html` / `.docs.md` chứa **Chi tiết từng tham số** + **Cách EA chạy** narrative) |
| `repro`   | `*spec*.yaml/yml/json`, `*.onnx`, `*.csv`                           | Tái tạo build từ spec + side-input ML / dataset                |
| _(root)_  | `manifest.json`                                                     | SHA-256 inventory + group index của toàn bộ zip                |

File ngoài bảng phân loại (`.txt` rời, file IDE, chính file `.zip`,
`manifest.json` cũ) bị bỏ qua. Bản `auto-build-report.json` trong zip
là snapshot build-side (build / lint / compile / gate / docs /
dashboard); bản trên disk được ghi lại sau bước package nên có thêm
`report.package.ok` + `report.package.groups` để CI grep được.

### 3.10. LLM-driven docs ship (`.docx` user-guide)

Pattern A — kit-light. Kit emit context + prompt → LLM agent (Devin /
Claude / Cursor) viết `guide.md` adaptive theo logic EA → kit convert
sang `.docx` cho ship.zip. Bộ đôi `mql5-docs-bundle` +
`mql5-docs-assemble` auto-run trong `mql5-auto-build`, hoặc gọi
standalone:

```bash
# Bước 1 — kit emit context + prompt (deterministic)
mql5-docs-bundle ea-spec.yaml MyEA/MyEA.mq5 --out MyEA/
# → MyEA/docs-context.json  (spec, inputs có semantic enrich, FLOW, build metrics)
# → MyEA/docs-prompt.md     (instructions Vietnamese cho LLM)

# Bước 2 — LLM agent đọc 2 file trên + viết `MyEA/guide.md`
# (bước này do agent thực hiện, kit không có LLM client)

# Bước 3 — kit convert markdown → Word docx
mql5-docs-assemble MyEA/guide.md --out MyEA/MyEA.docs.docx
# → MyEA/MyEA.docs.docx (ToC field cập nhật bằng F9, fonts Vietnamese
#   render đầy đủ; embed PNG charts từ MyEA/images/ nếu có)

# Hoặc all-in-one qua auto-build (bước 1 + bước 3 auto, bước 2 LLM agent):
mql5-auto-build ea-spec.yaml --out-dir MyEA/ --package
# → MyEA/docs-context.json + docs-prompt.md emit ngay sau build
# → Sau khi LLM agent ghi MyEA/guide.md → chạy mql5-docs-assemble
#   standalone, hoặc mql5-auto-build lần 2 (force=False để không xoá
#   guide.md).
```

`mql5-docs-bundle` không cần `auto-build-report.json` đã tồn tại;
truyền `--build-report MyEA/auto-build-report.json` nếu muốn nhúng
compile + lint metrics vào context (LLM dùng để viết chương "Risk
warnings" sát hơn).

`mql5-docs-assemble` validate `guide.md`: H1 đầu file là tên EA + version,
có `[[TOC]]` ngay sau, tối thiểu 5 chương — tối đa 12 chương. Vi phạm
sẽ surface vào `result.warnings` nhưng vẫn render docx để reviewer
preview.

Cả 2 lệnh **archetype-agnostic**: kit không hardcode cấu trúc chương cho
trend / scalping / DCA / ... — LLM tự adapt theo context. Xem
`scripts/vibecodekit_mql5/docs_bundle.py::REFERENCE_OUTLINE` để biết
cấu trúc tham chiếu mặc định (10 chương).

### 3.9. Other (5 lệnh)

```bash
# Verify pip-norm + multi-broker
python -m vibecodekit_mql5.broker_safety MyEA.mq5

# Trader-17 checklist (17 mục, pass threshold 15/17 — truyền MyEA.mq5
# positional, KHÔNG phải flag --mq5/--source)
python -m vibecodekit_mql5.trader_check MyEA.mq5

# 7-layer permission gate (truyền source positional, KHÔNG --source).
# Mode: personal (layer 1,2,3,4,7) | team (1-5,7) | enterprise (1-7).
mql5-permission --mode personal MyEA.mq5
mql5-permission --mode team     MyEA.mq5 --multibroker reports/
mql5-permission --mode enterprise MyEA.mq5 \
    --compile-log build.log --trader-check-report trader.json \
    --matrix quality-matrix.html --journal rri-bt.json

# Reconcile-install kit overlay vào project có sẵn
python -m vibecodekit_mql5.install ~/existing-mt5-project

# One-shot lint + Trader-17 second opinion (optional)
python -m vibecodekit_mql5.second_opinion MyEA.mq5
```

`mql5-permission` exit 1 nếu bất kỳ layer fail. Layer 2 (compile)
cần Wine + MetaEditor trên Linux — verify bằng `mql5-doctor --soft`; trong
CI chỉ chạy docs / lint thì bỏ `--mode enterprise` để không bị chen.

State dir (`--state-dir`, default `.rri-state`) cache payload từng
layer để lần chạy sau tái sử dụng.

**Wave 5.2 — sentinel content validator trên layer 5.** Layer
methodology (Layer 5) trước đây chỉ tin sentinel
``.rri-state/<step>.done`` mà không inspect nội dung step output, nên
operator (hoặc LLM agent) có thể ``touch`` sentinel mà không tick
checkbox nào trong ``## Activities`` của ``step-N-<name>.md``. Bật audit
bằng ``--enforce-activities``:

```bash
python -m vibecodekit_mql5.permission.layer5_methodology \
    --state-dir .rri-state --mode team --enforce-activities
```

Validator đọc companion ``step-N-<name>.md`` (cùng folder sentinel) và
tính tỉ lệ ``- [x]`` / ``- [ ]`` dưới ``## Activities``. Gate fail nếu
ratio dưới ngưỡng mặc định theo mode (`personal ≥ 50%`, `team ≥ 80%`,
`enterprise = 100%`); override bằng ``--activity-threshold 0.7``.
Companion thiếu / không có activities pass mặc định — validator
*additive*, không thay sentinel check cũ.

### 3.11. Forge closed loop (1 lệnh, Wave 3)

`mql5-forge-loop` chạy vòng lặp backtest hermetic trên Linux không cần
Wine. Mỗi iteration chain `mql5-fixture --type backtest` (deterministic
theo `--base-seed + i`) vào parser `mql5-backtest` và tổng hợp metric
từng iter vào 1 report duy nhất. Dùng để pin lint / parser contract
regression và chạy forge-style robustness sweep trong CI.

```bash
# Tối giản — 3 iteration strategy trend, deterministic seed 100:
mql5-forge-loop --iterations 3 --strategy trend --base-seed 100 \
                --out ./forge-loop/

# Có gate floor cứng — fail iter nào vượt ngưỡng:
mql5-forge-loop --iterations 5 --strategy mean-rev --base-seed 200 \
                --pf-floor 1.10 --sharpe-floor 0.80 --max-dd-ceiling 35.0 \
                --out ./forge-loop/ \
                --gate-report forge-loop-report.json --json

# Module-level:
python -m vibecodekit_mql5.forge_loop \
    --iterations 3 --strategy random --base-seed 42 --out ./forge-loop/
```

`mql5-forge-loop` ship Wave-1 `--json` envelope (`schema_version=1`)
+ `--gate-report`, nên matrix collector (`mql5-rri-matrix --collect`)
ăn unchanged. Không Wine, không MetaTester — fixture generator emit
XML/CSV/journal đúng schema mà backtest parser nhận.

### 3.12. Backtest engine — tick-bar simulator in-process (1 lệnh, Wave 3.E)

`mql5-bt-sim` sinh **OHLC tổng hợp** dưới random-walk có seed, chạy
một chiến lược long-only built-in, rồi emit XML đúng schema MT5
Strategy Tester. Parser `mql5-backtest` hiện tại ăn file đó unchanged
→ chain `mql5-bt-sim → mql5-backtest` để thay `mql5-fixture --type
backtest` mỗi khi agent muốn *logic entry / exit thật* trong vòng
lặp thay vì raw return synthesis.

Bốn strategy built-in:

| `--strategy`  | Logic                                                                                        |
|---------------|----------------------------------------------------------------------------------------------|
| `sma-cross`   | Cross SMA nhanh/chậm, long-only. Bar synth có drift dương → PF > 1.                          |
| `mean-rev`    | Kiểu Bollinger: vào long khi giá < SMA−k·σ, thoát ở SMA. AR(1) hệ số −0.5 trong bar synth.   |
| `breakout`    | Kênh Donchian: vào khi break đỉnh N-bar, thoát khi xuyên đáy N-bar. Edge xuất hiện khi trend. |
| `random`      | Baseline ngu (vào bar i%3==1, ra bar i%3==0). Dùng làm fixture không-edge.                    |

```bash
# Tối giản — sma-cross trên 500 bar tổng hợp, deterministic seed 42:
mql5-bt-sim --strategy sma-cross --bars 500 --seed 42 --out tester.xml

# Chain vào parser XML hiện tại unchanged:
mql5-backtest --report tester.xml --json

# Envelope JSON + gate-report cho matrix collector:
mql5-bt-sim --strategy mean-rev --bars 500 --seed 99 \
            --out tester.xml --returns-csv returns.csv \
            --json --gate-report gate-report-btsim.json

# Tune chu kỳ MA / band width mean-rev:
mql5-bt-sim --strategy sma-cross --fast 5 --slow 20 --bars 800 --seed 7 \
            --out tester.xml
mql5-bt-sim --strategy mean-rev  --slow 30 --k 2.5  --bars 800 --seed 7 \
            --out tester.xml

# Module-level:
python -m vibecodekit_mql5.bt_engine \
    --strategy breakout --bars 600 --seed 123 --out tester.xml
```

Cùng bộ ba `(strategy, seed, bars)` → XML byte-identical mỗi lần chạy.
Pure-Python, không depend, không Wine, không MetaTester. File
`--returns-csv` cũng vào thẳng `mql5-monte-carlo` /
`mql5-overfit-check` unchanged cho robustness phân tích downstream.

---

### 3.13. Agent prompts — 6 vai trò paste-and-run (Wave 5.3)

Kit **không** gọi LLM nào trong CLI. Khi muốn một LLM chat ngoài
(Claude, ChatGPT, Cursor, Devin) đóng đúng **một vai** ở **một step**,
copy file tương ứng dưới `docs/agent-prompts/` rồi paste làm system
message:

| File | Vai trò | Lens | Step chính |
|---|---|---|---|
| `strategy-architect.md` | Quant / chủ giả thuyết giao dịch | `ceo`, `investigate` | SCAN, RRI, VISION, REFINE |
| `broker-engineer.md` | Kỹ sư MQL5 — chủ code | `eng` | BLUEPRINT, TIP, BUILD, VERIFY |
| `risk-auditor.md` | Compliance / risk officer | `cso` | RRI, BLUEPRINT, VERIFY |
| `devops.md` | Deploy / VPS / observability | `eng` | BUILD, VERIFY, REFINE |
| `perf-analyst.md` | Phân tích backtest + tester | `investigate` | VERIFY, REFINE |
| `trader.md` | End-user — "chủ nhà" trong ẩn dụ chủ-thầu-thợ | `ceo` | SCAN, VISION, VERIFY |

Mỗi prompt có YAML frontmatter (`persona:`, `role:`, `review_lens:`,
`owns_steps:`, `contributes_steps:`, `peers:`, `inputs:`,
`outputs:`, `forbidden:`) + bộ section cố định cho operator
(`## Operating principles`, `## Step-by-step responsibilities`,
`## Handoff contracts`, `## What you must refuse to do`,
`## How to use this prompt`). Schema được găm bởi
`tests/gates/phase-C/test_agent_prompts_schema.py` để mọi prompt
luôn đồng nhất và machine-readable.

Bộ prompt này dùng song hành với generator Wave 5.1
(`mql5-vision-gen` / `mql5-blueprint-gen` / `mql5-tip-gen`):
generator emit skeleton deterministic, LLM dưới vai persona tương
ứng refine narrative. Cũng song hành với content validator Wave 5.2:
persona chưa "xong" step cho đến khi `step-N-<name>.md` có đủ
checkbox `## Activities` được tick để vượt ngưỡng theo mode
(`personal ≥ 50%`, `team ≥ 80%`, `enterprise = 100%`).

Xem `docs/agent-prompts/README.md` cho playbook operator (English +
Tiếng Việt).

---

### 3.14. Triangle of Power — 3 vai actor + contract + verify-report (Wave 6.1)

Wave 6.1 thêm một tầng governance bên trên 6 persona Wave 5.3. Kit
giờ ship 3 **actor prompt** dưới `docs/agent-prompts/actors/`, cộng
với 2 emitter CLI mới và một mở rộng layer-5 permission gate để audit
ritual sign-off thủ công giữa các actor.

#### 3.14.1. Ba actor (Tam giác quyền lực)

| File | Vai trò | Persona con (Wave 5.3) | Sở hữu | Sign-off |
|---|---|---|---|---|
| `chu-nha.md` | **Chủ nhà** — operator con người | `trader` | SCAN, VISION (quyết), REFINE (quyết) | `APPROVED by <tên>` trên blueprint, `CONFIRM by <tên>` trên contract |
| `chu-thau.md` | **Chủ thầu** — ghế thiết kế (Claude Chat / GPT-4 / Cursor Ask) | `strategy-architect`, `risk-auditor` | VISION (thiết kế), BLUEPRINT, CONTRACT, TASK-GRAPH, VERIFY-REPORT | Emit khối `CHECKPOINT` + `CONFIRM`; KHÔNG bao giờ chạy build/compile |
| `tho-thi-cong.md` | **Thợ thi công** — ghế triển khai (Claude Code / Devin / Cursor Edit) | `broker-engineer`, `devops`, `perf-analyst` | SCAN (thực thi), TIP triển khai, BUILD, VERIFY run | Emit Completion Report + `gate-report-*.json` mỗi step |

Mỗi file actor khai báo `sub_personas:` (binding sang 6 persona Wave
5.3), graph edge `escalates_to:` / `delegates_to:`, và allow-list
`forbidden_tools:`. Sáu persona Wave 5.3 hiện có thêm field
`super_actor:` neo về actor cha; cả hai schema được pin bởi
`tests/gates/phase-C/test_actor_prompts_schema.py` và
`tests/gates/phase-C/test_agent_prompts_schema.py`.

#### 3.14.2. `mql5-contract-gen` — emitter contract Step 4.5

Chủ thầu emit contract gửi Chủ nhà từ Step-4 blueprint đã APPROVED
cộng với `ea-spec.yaml` canonical:

```bash
mql5-contract-gen step-4-blueprint.md \
    --ea-spec ea-spec.yaml \
    --out contract.md
```

Output có 6 section cố định (`## DELIVERABLES`, `## EXCLUSIONS`,
`## TECH STACK`, `## INVARIANTS`, `## TASK GRAPH SUMMARY`,
`## ACCEPTANCE OVERVIEW`) theo sau bởi khối thủ công `## CONFIRM`
Chủ nhà phải điền (`CONFIRM by <tên> at <YYYY-MM-DD>`). Bullet
deliverable/exclusion được preset-key (`trend`, `mean-rev`,
`breakout`, `grid`, `martingale`, `scalping`, `swing`, `news`, …) nên
cùng `(preset, stack)` luôn cho ra cùng nội dung contract. CLI hỗ
trợ envelope `--json` chuẩn + `--gate-report <path>`.

Nếu blueprint thiếu dòng `APPROVED by …`, contract header chèn callout
`> WARNING` để operator nhận biết trước khi forward.

#### 3.14.3. `mql5-verify-report` — aggregator Step 7

Sau khi Thợ thi công đã chạy mọi Wave-1 gate và drop
`gate-report-*.json` vào thư mục, Chủ thầu aggregate thành một
verify-report Markdown duy nhất:

```bash
mql5-verify-report \
    --gate-reports reports/ \
    --blueprint step-4-blueprint.md \
    --tip-dir tasks/ \
    --completion-dir completions/ \
    --out verify-report.md
```

Report derive `OVERALL STATUS = READY | NEEDS_FIXES | MAJOR_ISSUES`,
phân loại gate thành Tech Health / Scenario Results / Other, phơi
mọi FAIL kèm path, và (khi cấp blueprint + TIP dir) emit bảng
coverage `INVARIANT ↔ TIP` bằng greedy keyword match. Cũng roll-up
mọi dòng STATUS từ `completion-*.md` và kết thúc bằng menu 4 lựa
chọn REFINE (`Ship as-is`, `Tighten`, `Add tests`, `Reopen VISION`)
để Chủ thầu đưa Chủ nhà bản nháp quyết định.

#### 3.14.4. `mql5-permission-layer5 --enforce-sign-off` — audit con dấu thủ công

Layer-5 gate giờ optional enforce ritual sign-off:

```bash
mql5-permission-layer5 \
    --state-dir .rri-state/ \
    --mode team \
    --enforce-activities \
    --enforce-sign-off \
    --blueprint step-4-blueprint.md \
    --contract contract.md
```

Audit tìm `APPROVED by <tên> at <ngày>` trên blueprint và
`CONFIRM by <tên> at <ngày>` trên contract, capture signer + ngày,
tính sha256 canonical trên body **trừ đi** dòng sign-off. Mọi mutation
body sau khi đã ký sẽ silently đổi hash để reviewer detect re-edit.
Personal mode contract sign-off optional; team/enterprise mode cả hai
đều bắt buộc. Flag compose với `--enforce-activities` (Wave 5.2) —
một lệnh chạy được cả hai check.

---

### 3.15. Task Graph + Completion Report (Wave 6.2)

Wave 6.2 mở rộng contract `chu-nha` đã ký thành DAG nhiều TIP và đưa
ra **shape cố định** cho Completion Report mà `tho-thi-cong` phải nộp
khi hoàn thành mỗi TIP.

#### 3.15.1. `mql5-task-graph-gen` — bung `contract.md` thành nhiều file TIP

`chu-thau` chạy ngay sau khi `chu-nha` ký `contract.md`:

```bash
mql5-task-graph-gen contract.md --out-dir .
```

Output (deterministic — cùng contract → cùng file):

* `tasks/TIP-001.md` … `tasks/TIP-NNN.md` — một file mỗi dòng
  `TIP-NNN — <desc>` trong `## TASK GRAPH SUMMARY`. Frontmatter YAML
  (`tip_id`, `title`, `status: PENDING`, `actor: tho-thi-cong`,
  `depends_on: [...]`, `invariant_refs: [...]`,
  `contract_sha256_prefix:`) + 4 section markdown (`## Goal`,
  `## Acceptance criteria`, `## Dependencies`, `## Completion`).
* `task-graph.md` — diagram Mermaid `graph TD` của các cạnh phụ
  thuộc + bảng index cross-link mọi TIP với actor và số invariant
  liên quan.

Cạnh DAG resolve hoàn toàn theo classifier keyword trên description
từng TIP:

| Loại | Keyword | Phụ thuộc vào |
|---|---|---|
| `scaffold` | `scaffold` | _none — root_ |
| `risk` | `risk guard`, `risk per` | mọi TIP scaffold |
| `signal` | `signal` | mọi TIP risk (fallback: scaffold) |
| `filter` | `filter` | mọi TIP signal (fallback chain) |
| `backtest` | `backtest`, `walk-forward` | mọi filter + signal |
| `permission` | `permission`, `gate` | mọi backtest |
| `other` | (còn lại) | TIP liền trước |

Invariants từ `## INVARIANTS` của contract được cross-link vào
frontmatter từng TIP bằng greedy match token ≥ 6 ký tự alphabetic,
giúp `tho-thi-cong` biết TIP đang implement invariant BLUEPRINT nào.
Classifier + matcher deterministic — chạy lại trên cùng contract sẽ
sinh ra file byte-identical. Hỗ trợ `--json` envelope chuẩn và
`--gate-report <path>`.

Thêm `--force` để overwrite `tasks/TIP-*.md` hoặc `task-graph.md`
nếu đã tồn tại (mặc định CLI refuse với exit code 2).

#### 3.15.2. `mql5-completion-report` — STATUS / Files / Tests / Issues từng TIP

Sau khi `tho-thi-cong` xong một TIP, emit Completion Report bằng
file TIP + directory gate-report envelope Wave-1:

```bash
mql5-completion-report \
    --tip tasks/TIP-001.md \
    --gate-reports reports/TIP-001/ \
    --file Include/CRiskGuard.mqh \
    --file TrendEA.mq5 \
    --test tests/gates/phase-D/test_risk_guard.py \
    --out completions/completion-001.md
```

Output (`completion-001.md`):

* `# Completion Report — TIP-001`
* `**TITLE:**`, `**STATUS:**` (READY / IN_PROGRESS / BLOCKED),
  `**ACTOR:** tho-thi-cong`, path TIP source + sha256 prefix
* `## Files Changed` — mỗi `--file` 1 bullet
* `## Tests Added` — mỗi `--test` 1 bullet
* `## Issues Encountered` — mỗi `--issue` 1 bullet
* `## Gate Reports Referenced` — bảng auto-generate (Tool / Status /
  Summary / Path) cho mọi envelope Wave-1 dưới `--gate-reports`
* `## Invariants Referenced` — copy verbatim từ frontmatter TIP

Status derive deterministic:

| Điều kiện | STATUS |
|---|---|
| Có envelope `FAIL` HOẶC có `--issue` | `BLOCKED` |
| Toàn `PASS`/`WARN`, không có FAIL/issue | `IN_PROGRESS` (nếu có WARN) hoặc `READY` (toàn PASS) |
| Không load envelope nào | `IN_PROGRESS` |

CLI emit envelope `--json` chuẩn + `--gate-report <path>`. Khi STATUS
= BLOCKED exit code = 1 (cho CI / shell chain short-circuit); ngược
lại exit code = 0. CLI **cố ý không** sửa field `status:` trong
frontmatter TIP — đó là quyết định manual của `tho-thi-cong` sau khi
đọc report. `mql5-verify-report` (Wave 6.1) pick-up các
`completion-*.md` qua flag `--completion-dir`.

#### 3.15.3. Luồng end-to-end

```
CHỦ-NHÀ ký blueprint                  (APPROVED by <tên>)
        │
        ▼
CHỦ-THẦU chạy mql5-contract-gen
        │
        ▼
CHỦ-NHÀ ký contract                   (CONFIRM by <tên>)
        │
        ▼
CHỦ-THẦU chạy mql5-task-graph-gen     → tasks/TIP-001..N.md + task-graph.md
        │
        ▼
THỢ THI CÔNG nhận TIP gốc → implement → emit gate-report-*.json
        │
        ▼
THỢ THI CÔNG chạy mql5-completion-report → completions/completion-NNN.md
        │
        ▼
CHỦ-THẦU chạy mql5-verify-report      → verify-report.md
        │
        ▼
CHỦ-NHÀ chọn REFINE option (Ship / Tighten / Add tests / Reopen VISION)
```

### 3.16. Log escalation actor-to-actor (Wave 6.2b)

Khi một vai trong Tam giác quyền lực không thể tiếp tục mà không có input
từ vai khác, họ **escalate** thay vì đoán mò. Kit lưu log JSONL append-only
ở `.mql5-audit/escalations.jsonl` để audit trail compose tự nhiên với git.

Ba mức được công nhận:

| Mức | Ý nghĩa | Chặn `mql5-permission-layer5` (với `--enforce-no-open-escalation`)? |
|----:|---------|---------------------------------------------------------------------|
| 1 | Note / quan sát | Không |
| 2 | Cảnh báo / hỏi | Không (thông tin; xuất hiện trong Verify Report) |
| 3 | Chặn cứng       | **Có** — gate TEAM / ENTERPRISE fail khi còn L3 OPEN |

#### 3.16.1. `mql5-escalation` — raise / list / resolve

```bash
# Raise (Thợ thi công hỏi Chủ thầu vì thiếu CPipNormalizer):
mql5-escalation \
    --from tho-thi-cong \
    --to   chu-thau \
    --level 3 \
    --reason "thiếu CPipNormalizer cho XAUUSD; pip math sai" \
    --artefact tasks/TIP-002.md

# List (mặc định lọc OPEN; --status RESOLVED|ALL cũng hợp lệ):
mql5-escalation --list
mql5-escalation --list --status ALL --level 3

# Resolve (Chủ thầu xác nhận + ghi giải pháp):
mql5-escalation \
    --resolve ESC-20260525-001 \
    --resolved-by chu-thau \
    --note "đã patch include/CPipNormalizer.mqh"
```

Hành vi:

- Mỗi record có id deterministic `ESC-YYYYMMDD-NNN` được cấp phát bằng
  một lần scan log hiện có nên hai lần gọi cùng ngày không bao giờ trùng.
- `--from` và `--to` phải khác nhau và phải thuộc
  `chu-nha` / `chu-thau` / `tho-thi-cong`.
- `--reason` bắt buộc và phải khác rỗng sau khi strip.
- Override log path: `--audit-log <path>` (mặc định
  `.mql5-audit/escalations.jsonl`).
- Cờ envelope Wave-1 chuẩn: `--json` cho stdout, `--gate-report <path>`
  để persist.
- Idempotency: resolve lại record `RESOLVED` raise error thay vì
  ghi đè im lặng note cũ.

#### 3.16.2. Hook layer-5 — `--enforce-no-open-escalation`

```bash
# Gate TEAM fail khi còn L3 escalation OPEN:
mql5-permission-layer5 \
    --mode team \
    --enforce-no-open-escalation

# Personal mode: chỉ báo cáo số lượng, không fail (giữ backward compat):
mql5-permission-layer5 \
    --mode personal \
    --enforce-no-open-escalation

# Override log path (compose với --enforce-activities + --enforce-sign-off):
mql5-permission-layer5 \
    --mode enterprise \
    --enforce-no-open-escalation \
    --escalation-log .mql5-audit/escalations.jsonl \
    --enforce-sign-off \
    --enforce-activities
```

Envelope thêm ba field mới dưới `data`:

```json
{
  "escalation_log": ".mql5-audit/escalations.jsonl",
  "escalation_open_level3_count": 1,
  "escalation_open_level3": [
    {"id": "ESC-20260525-001", "from": "tho-thi-cong",
     "to": "chu-thau", "level": 3, ...}
  ],
  "escalation_enforced": true
}
```

`escalation_enforced` chỉ `true` khi `mode != "personal"` để operator xem
report personal mode lập tức thấy số lượng là thông tin, không phải verdict.

#### 3.16.3. Khi nào dùng mức nào

- **Level 1 (note):** Thợ thi công phát hiện magic number collision có sẵn
  khi implement một TIP. Không chặn TIP này, nhưng Chủ thầu cần biết.
- **Level 2 (cảnh báo):** Thợ phát hiện acceptance criteria của TIP mâu
  thuẫn với một invariant. Cần Chủ thầu quyết trước TIP kế, nhưng TIP
  hiện tại vẫn ship được.
- **Level 3 (chặn cứng):** Thợ không thể hoàn thành TIP-002 vì contract
  giả định có `CPipNormalizer` nhưng không có. Gate TEAM / ENTERPRISE
  từ chối ship đến khi Chủ thầu sửa contract hoặc cung cấp include
  thiếu.

---

## 4. Ví dụ hoàn chỉnh: MACD+SAR EURUSD H1

Worked example đầy đủ ở `examples/ea-wizard-macd-sar-eurusd-h1-portfolio/`.
Đây là turnaround **4 tiếng ở chế độ enterprise** trên Devin VM.

### Bước 1 — SCAN (5 phút)
```bash
python -m vibecodekit_mql5.scan ~/projects/eurusd-portfolio
# Kết quả: cây trống
```

### Bước 2 — RRI (90 phút, enterprise)
```bash
python -m vibecodekit_mql5.rri.step_workflow --mode enterprise
# 6 persona × 25 câu = 150 câu hỏi
# Output: docs/rri-report.md
```

### Bước 3 — VISION (15 phút)
Mở template `docs/rri-templates/step-3-vision.md.tmpl` và điền:
- Hypothesis: MACD signal cross gated by Parabolic-SAR flip
- Scope: EURUSD H1 netting account
- Out of scope: hedging, multi-symbol, news filter

### Bước 4 — BLUEPRINT (30 phút)
Mở `step-4-blueprint.md.tmpl`. Quyết định:
- Archetype: `wizard-composable/netting`
- Includes cần dùng: `CPipNormalizer`, `CRiskGuard`, `CMagicRegistry`, `CMfeMaeLogger`
- Magic number: 5001

### Bước 5 — TIP (8 TIP, ~30 phút)
8 Technical Implementation Points — chi tiết về SL/TP, risk per trade,
filter, trailing, kill switch, slippage limit, news blackout, weekly DD cap.

### Bước 6 — BUILD (10 phút)
```bash
python -m vibecodekit_mql5.wizard \
    --name EAMacdSarPortfolio \
    --symbol EURUSD --tf H1 \
    --output ~/projects/eurusd-portfolio
```

### Bước 7 — VERIFY (multi-stage, ~60 phút)
```bash
# Code-quality (chạy ngay, không cần XML report)
python -m vibecodekit_mql5.compile             EAMacdSarPortfolio.mq5
python -m vibecodekit_mql5.lint                EAMacdSarPortfolio.mq5
python -m vibecodekit_mql5.method_hiding_check EAMacdSarPortfolio.mq5

# Chạy Strategy Tester (manual / qua MT5 GUI), thu XML report sau đó:
python -m vibecodekit_mql5.backtest      EAMacdSarPortfolio.ex5 default.set \
    --period H1 --symbol EURUSD --report tester.xml > metrics.json
python -m vibecodekit_mql5.walkforward   is.xml oos.xml      > walkforward.json
python -m vibecodekit_mql5.monte_carlo   returns.csv --reported-dd 5.4 \
                                         --n-sims 1000        > montecarlo.json
python -m vibecodekit_mql5.overfit_check is.xml oos.xml      > overfit.json
python -m vibecodekit_mql5.multibroker   --reports a.xml,b.xml,c.xml
python -m vibecodekit_mql5.trader_check  EAMacdSarPortfolio.mq5 > trader-check.json

# Quality matrix + RRI review
python -m vibecodekit_mql5.rri.rri_bt    --metrics metrics.json \
                                         --mode enterprise --output rri-bt.html
python -m vibecodekit_mql5.rri.rri_rr    --trader-check trader-check.json \
    --walkforward walkforward.json --monte-carlo montecarlo.json \
    --overfit overfit.json --mode enterprise --output rri-rr.html
```

### Bước 8 — REFINE + SHIP (~10 phút)
```bash
python -m vibecodekit_mql5.refine --diff change.patch
python -m vibecodekit_mql5.ship --tag v1.0.0 --dry-run
python -m vibecodekit_mql5.ship --tag v1.0.0
```

Kết quả: EA `EAMacdSarPortfolio.ex5` + `.set` file + ma trận 64 ô +
backtest XML + MFE/MAE report + canary log — đầy đủ 5 artefact ở
`examples/ea-wizard-macd-sar-eurusd-h1-portfolio/results/`.

---

## 5. Tích hợp 4 MCP server

Kit ship 4 MCP server theo chuẩn JSON-RPC 2.0 over stdio. Dùng được
từ bất kỳ MCP client nào (Claude Desktop, Cursor, Codex, Devin, …).

### 5.1. metaeditor-bridge

3 tool: `metaeditor.compile`, `metaeditor.parse_log`, `metaeditor.includes_resolve`

Khởi động:
```bash
python mcp/metaeditor-bridge/server.py
```

### 5.2. mt5-bridge (READ-ONLY)

10 tool **chỉ-đọc** (KHÔNG có `order_send`, `order_close`, hay
`position_modify` — được enforce bằng test `test_mt5_bridge_readonly_no_trade`):

- `mt5.symbols.list`, `mt5.symbol.info`
- `mt5.rates.copy`, `mt5.tick.last`
- `mt5.account.info`, `mt5.terminal.info`
- `mt5.positions.list`, `mt5.positions.history`
- `mt5.history.deals`, `mt5.market.book`

Khởi động:
```bash
python mcp/mt5-bridge/server.py
```

> ⚠️ **Lưu ý platform:** package `MetaTrader5` chỉ cài được trên
> **Windows** (hoặc Wine MT5 desktop qua `winetricks`). Trên Linux VM
> thuần, import fail và mọi tool trả **stub payload** cố định
> (symbol list rỗng, 0 bar, `digits=5, point=0.00001` hardcoded cho
> `mt5.symbol.info`). Stub giữ MCP contract test hermetic được nhưng
> **không phải data thật**. Để có market/account data live, chạy
> server này trên Windows hoặc Wine MT5.

### 5.3. algo-forge-bridge

6 tool: `forge.init`, `forge.clone`, `forge.commit`, `forge.pr.create`,
`forge.pr.list`, `forge.repo.list`. Cần `ALGO_FORGE_API_KEY` env var.

Khởi động:
```bash
ALGO_FORGE_API_KEY=xxx python mcp/algo-forge-bridge/server.py
```

### 5.4. vibecodekit-bridge

29 tool qua 6 PR. Cho phép AI coding agent (Codex CLI / Claude Code /
Cursor / Devin / Claude Desktop) gọi thẳng vào pipeline `prompt → spec
→ build → verify → review → ship` qua JSON-RPC. Wire format ổn định
giữa các PR — PR sau chỉ mở rộng `DISPATCH`.

**PR-1 (prompt → spec → build → permission gate):**
`spec.from_prompt`, `spec.validate`, `build.auto`, `verify.permission`.

**PR-2 (static-analysis verify suite):** `verify.lint` (8 AP critical),
`verify.lint_best_practice` (17 AP WARN), `verify.method_hiding`,
`verify.trader17`, `verify.compile`, `verify.broker_safety`,
`verify.audit`.

**PR-3 (runtime / statistical verify suite):** `verify.backtest`
(parser XML report của MT5 tester), `verify.walkforward` (tương quan
Sharpe OOS/IS + verdict), `verify.montecarlo` (stress test DD theo
bootstrap), `verify.multibroker` (ổn định N-broker: PF CV / Sharpe
stdev / DD diff), `verify.fitness` (tra cứu template `OnTester()`),
`verify.mfe_mae` (thống kê excursion từ CSV), `verify.overfit` (verdict
Sharpe IS/OOS — không cần XML).

**PR-4 (review / RRI suite):** `review.eng` (broker-engineer + devops),
`review.cso` (risk-auditor), `review.ceo` (trader + strategy-architect),
`review.investigate` (perf-analyst + strategy-architect), và
`rri.persona` (generic 1-persona x 1-step x 1-mode). Mỗi tool trả về
markdown sẵn sàng dán vào PR description hoặc file `review.md`.

**PR-5 (ship-stage tools):** `dashboard.publish` render dashboard
quality-matrix 64 cell từ pipeline digest và publish qua command tùy
chọn (fallback `file://` URI khi không cấu hình command). `forge.pr.create`
mở PR trên MQL5 Algo Forge — gọi HTTP thật khi có `MQL5_FORGE_TOKEN`,
không thì trả về dry-run payload (kèm `endpoint` + `planned_payload`).
Chain hai tool này để nhúng URL dashboard public vào body của Forge PR.

**Schema `ea-spec.yaml` mở rộng (PR-2 + PR-8):** thêm 8 block optional,
full back-compat. PR-2 cho 3 block đầu — `prop_firm` (DD limits + news
block + weekend-flat cho FTMO/MFF), `time_exit` (close on Friday, max
trade hours, session windows), `stealth` (random slippage / comment
pool / lot jitter, split orders). PR-8 thêm 5 block: `trailing`
(trailing-stop kiểu fixed / ATR / parabolic), `partial_close` (scale-
out nhiều mức + move-SL-về-breakeven sau mức đầu), `correlation` (max
vị thế correlated, ngưỡng Pearson, symbol group, block-on-correlated-
loss), `swap_filter` (giới hạn swap pip/ngày theo hướng, skip thứ tư
triple-swap), `logs` (level, file pattern, terminal output, redact số
tài khoản). Spec cũ không có các block này vẫn validate như cũ.

**PR-7 (discovery / fix-loop helpers):** `discover.doctor` chạy
doctor của kit (Python / Wine / MetaEditor / module + scaffold bắt
buộc), `discover.scan` quét workspace và phân loại theo extension
(`.mq5` → ea-source, `.mqh` → include, `.set` → tester-set, `.ex5`
→ compiled, `.onnx` → onnx-model), `discover.llm_context` wire 1
trong 3 LLM-bridge scaffold pattern (`cloud-api` / `self-hosted-
ollama` / `embedded-onnx-llm`) vào EA `.mq5` có sẵn, và
`verify.auto_fix` chạy AP auto-fixer trên file (rewrite in-place)
hoặc trên source string in-memory. Pair `verify.lint` ↔
`verify.auto_fix` để đóng fix-loop cho agent mà không cần rời
bridge.

```bash
python mcp/vibecodekit-bridge/server.py
```

Wire format ổn định từ PR-1 → PR-5 → PR-7 → PR-8 và các PR sau
(PR-8 chỉ thêm field vào schema spec, không đụng surface bridge).


### 5.5. Cấu hình MCP client

Xem [docs/ENV-SETUP-vi.md](ENV-SETUP-vi.md) cho cấu hình cụ thể từng
IDE/CLI (Claude Desktop, Cursor, Codex, Devin).

---

## 6. 26 anti-pattern detector

Lint chia 2 cấp:

### 6.1. Critical APs — ERROR, block ship (8)

| ID | Mô tả | Detector ở đâu |
|----|------|----------------|
| AP-1 | `OrderSend` không có SL | `scripts/vibecodekit_mql5/lint.py` |
| AP-3 | Lot cố định, không risk-based | `lint.py` |
| AP-5 | EA overfit (in-sample only, không OOS) | `lint.py` |
| AP-15 | `OrderSend` thô, không qua `CTrade` | `lint.py` |
| AP-17 | `WebRequest` gọi trong `OnTick` | `lint.py` |
| AP-18 | `OrderSendAsync` thiếu `OnTradeTransaction` handler | `lint.py` |
| AP-20 | Hardcode pip (`* 0.0001`, `* _Point`) | `lint.py` |
| AP-21 | JPY/XAU digits broken (`digits-tested:` < 2 class) | `lint.py` |

### 6.2. Best-practice APs — WARN, không block (17)

| ID | Mô tả | Detector |
|----|------|---------|
| AP-2 | SL quá chặt | `lint_best_practice.py` |
| AP-4 | Martingale không có cap | `lint_best_practice.py` |
| AP-6 | Curve-fitted optimization | `lint_best_practice.py` |
| AP-7 | Magic number hardcode | `lint_best_practice.py` |
| AP-8 | Không có spread guard | `lint_best_practice.py` |
| AP-9 | Multi-entry trên cùng bar | `lint_best_practice.py` |
| AP-10 | `OrderSend` không check return | `lint_best_practice.py` |
| AP-11 | EA blind về mode (netting vs hedging) | `lint_best_practice.py` |
| AP-12 | Leak indicator handle (không release) | `lint_best_practice.py` |
| AP-13 | EA broker-coupled (`SymbolInfoDouble` hardcode) | `lint_best_practice.py` |
| AP-14 | Không log MFE/MAE | `lint_best_practice.py` |
| AP-16 | Reinvent stdlib (tự code thay vì `CTrade`) | `lint_best_practice.py` |
| AP-19 | ONNX không validate trên Strategy Tester | `lint_best_practice.py` |
| AP-22 | `OnTick` không đặt lệnh (signal placeholder) | `lint_best_practice.py` |
| AP-23 | `CTrade.Buy/Sell` không check return/retcode | `lint_best_practice.py` |
| AP-24 | Đọc history/chỉ báo khi chưa có sync guard | `lint_best_practice.py` |
| AP-25 | `delete` thô không có pointer guard | `lint_best_practice.py` |

### 6.3. Method-hiding (1, build-aware)

Build MetaEditor ≥ 5260 báo ERROR khi subclass `CExpert` có method
trùng tên với base class mà thiếu `using BaseClass::method;`. Build
< 5260 chỉ WARN.

```bash
python -m vibecodekit_mql5.method_hiding_check MyEA.mq5 --build 5260
```

---

## 7. Troubleshooting

### "wine: command not found"
- Linux: `./scripts/setup-wine-metaeditor.sh` chưa chạy thành công.
- macOS: `brew install --cask wine-stable`.
- Windows: không cần Wine — đặt `METAEDITOR_BIN=C:\Path\To\metaeditor64.exe`.

### `python -m vibecodekit_mql5.doctor` báo "metaeditor-bin: not found"
- Đặt biến môi trường `METAEDITOR_BIN`:
  ```bash
  export METAEDITOR_BIN=~/.wine/drive_c/Program\ Files/MetaTrader\ 5/metaeditor64.exe
  ```

### `doctor --soft` cho CI chỉ chạy docs / lint (không có Wine)
Các probe Wine / MetaEditor / terminal chuyển thành cảnh báo thay vì lỗi, để
CI không có Wine vẫn exit 0. Các check bắt buộc (Python ≥ 3.10, import kit
package, `docs/references/`, scaffold archetypes) vẫn flip gate như cũ.
```bash
python -m vibecodekit_mql5.doctor --soft
# JSON output có thêm "soft": true và "strict_ok": <ok không lọc>
# rc == 0 khi chỉ có probe optional wine/MT5 fail; rc == 1 nếu bất kỳ
# check bắt buộc nào fail.
```

### Test ONNX e2e fail vì PyTorch không cài
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install onnx onnxscript
```

### `audit-plan-v5.py --post-phase=E` báo missing scaffold
- Chạy `git status` xem có file scaffold nào untracked không.
- Kiểm tra `.gitignore` không loại nhầm artefact:
  ```bash
  git check-ignore -v examples/**/results/canary.log
  ```

### MCP server `mt5-bridge` báo "MetaTrader5 not installed"
```bash
pip install MetaTrader5  # chỉ chạy được trên Windows hoặc Wine với MT5 desktop
```

### `forge_init` báo 401 Unauthorized
- Đặt `ALGO_FORGE_API_KEY` qua secrets manager hoặc env var:
  ```bash
  export ALGO_FORGE_API_KEY=your_key_here
  ```

### "Linguist phân loại repo là MQL4 thay vì MQL5"
- Đã fix ở `.gitattributes` (PR #17). Nếu vẫn thấy MQL4 trên GitHub
  language bar, đợi 10 phút sau commit để GitHub re-run Linguist.

---

## Tài nguyên bổ sung

- [`docs/COMMANDS.md`](COMMANDS.md) — Bảng tra cứu 69 lệnh CLI (59 standalone + 10 alias Wave-3)
- [`docs/agent-prompts/`](agent-prompts/) — 6 persona prompt paste-and-run (Wave 5.3) + README operator playbook
- [`docs/references/`](references/) — 29 cheatsheet kỹ thuật (50-survey → 80-input-syntax)
- [`docs/PLAN-v5.md`](PLAN-v5.md) — Spec gốc 1089 dòng
- [`docs/anti-patterns-AVOID.md`](anti-patterns-AVOID.md) — Anti-pattern phải tránh từ VCK-HU
- [`docs/rri-personas/`](rri-personas/) — 6 file YAML × 25 câu hỏi
- [`docs/rri-templates/`](rri-templates/) — 8 template markdown step-by-step
- [`examples/ea-wizard-macd-sar-eurusd-h1-portfolio/`](../examples/ea-wizard-macd-sar-eurusd-h1-portfolio/) — Worked example 4 tiếng

Câu hỏi / báo lỗi → mở issue trên
https://github.com/VibeMql5Codekit/vibecodekit-mql5-ea-25.5/issues
