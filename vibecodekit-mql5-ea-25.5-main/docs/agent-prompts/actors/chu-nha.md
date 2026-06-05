---
actor: chu-nha
display_name: Chủ nhà — Homeowner / Product Owner
runs_in: human (the operator of the kit)
sub_personas: [trader]
owns_steps: [scan, vision, refine]
contributes_steps: [rri, verify]
forbidden_steps: [tip, build]
escalates_to: null
delegates_to: chu-thau
escalation_level_threshold: 3
inputs:
  - Free-text problem statement / trading thesis
  - Account broker / instrument / risk appetite
  - Constraints from the business (capital, mandate, jurisdiction)
outputs:
  - APPROVED token at the end of step-4-blueprint.md
  - CONFIRM token at the end of contract.md
  - Sign-off on docs/USAGE-*.md "Operator's checklist"
forbidden_tools:
  - mql5-blueprint-gen     # blueprint design is delegated to chu-thau
  - mql5-tip-gen           # task graph generation is delegated to chu-thau
  - mql5-auto-build        # implementation is delegated to tho-thi-cong
  - mql5-compile           # compilation is delegated to tho-thi-cong
allowed_tools:
  - mql5-init
  - mql5-spec-from-prompt
  - mql5-contract-sign     # Wave 6.1 — sign the contract artefact
  - mql5-permission        # to inspect (read-only) gate status
peers: []
---

# Chủ nhà — agent prompt (Vietnamese; English mirror below)

Bạn là **Chủ nhà** trong tam giác quyền lực của VIBECODE Kit / vibecodekit-mql5-ea.
Bạn là **con người duy nhất** trong ba vai — Chủ thầu là Claude Chat (hoặc
LLM tương đương), Thợ thi công là Claude Code (hoặc Devin / Cursor).
Bạn không cần biết MQL5, MetaTrader, hay broker API. Bạn cần biết
**bạn muốn gì** và **bạn không chấp nhận điều gì**.

## Operating principles

1. **Ra quyết định, không ra implementation.** Bạn nói "tôi cần EA trend
   EURUSD H1, rủi ro 0.5% per trade", **không** nói "dùng ATR 14 với
   trailing stop 1.5×ATR". Chi tiết kỹ thuật do Chủ thầu đề xuất, bạn
   approve/reject.
2. **Approve = khế ước.** Khi bạn reply "APPROVED" ở cuối
   `step-4-blueprint.md` hoặc "CONFIRM" ở cuối `contract.md`, bạn đang
   ký một khế ước. Sau đó kiến trúc **không đổi** trừ khi quay lại
   Step 3 (VISION).
3. **Bạn là cây cầu.** Không có giao thức chat trực tiếp giữa Claude Chat
   và Claude Code. Mọi TIP đi xuống và Completion Report đi lên đều do
   bạn copy-paste qua lại.
4. **Bạn từ chối được.** Nếu Chủ thầu đề xuất kiến trúc bạn không hiểu,
   bạn bảo "giải thích bằng 3 câu, mỗi câu ≤ 15 từ" thay vì gật bừa.

## Step-by-step responsibilities

### Step 1 — SCAN
Bạn cung cấp context Chủ thầu không có: tên broker thật, lịch sử account,
ràng buộc compliance (vd "không được short cổ phiếu Việt Nam"). Bạn
**không** chạy `mql5-scan` trực tiếp — bạn relay output `mql5-scan` từ
Thợ thi công về Chủ thầu.

### Step 2 — RRI
Bạn **trả lời** 5-câu (personal mode) hoặc 25-câu (enterprise mode) cho
mỗi persona Chủ thầu yêu cầu. Câu nào không biết, trả lời "tôi cần Chủ
thầu đề xuất rồi tôi approve/reject" — đừng đoán.

### Step 3 — VISION
Bạn **đọc** `step-3-vision.md` Chủ thầu sinh ra. Reject nếu:
- Scope vượt ngân sách (vd "kit gợi ý 10 tuần build, tôi chỉ có 3 tuần").
- Có item mâu thuẫn với business (vd "giao dịch trong giờ trưa khi
  bạn cấm").
- Có giả định bạn không bao giờ kiểm tra được.

### Step 4 — BLUEPRINT (+ CHECKPOINT)
Bạn **đọc kỹ** module diagram + invariants + state machine. Khi mọi thứ
ổn, reply chính xác chuỗi sau ở cuối file:

```
APPROVED by <tên bạn> at <YYYY-MM-DD>
```

Chủ thầu/sentinel sẽ chạy `mql5-permission-layer5 --enforce-sign-off`
để verify dòng này tồn tại + hash của blueprint không thay đổi sau khi
ký.

### Step 4.5 — CONTRACT (+ CONFIRM)
Sau khi blueprint APPROVED, Chủ thầu sinh `contract.md` bằng
`mql5-contract-gen step-4-blueprint.md --out contract.md`. Bạn đọc
deliverables + exclusions + task graph summary. Khi đồng ý:

```
CONFIRM by <tên bạn> at <YYYY-MM-DD>
```

Sau dòng này, Thợ thi công bắt đầu thi công.

### Step 5-6 — BUILD (vai trò relay)
Bạn copy `tasks/TIP-NNN.md` cho Thợ thi công. Khi Thợ emit
`completion-NNN.md`, bạn copy về Chủ thầu. Bạn **không** debug, bạn
chỉ chuyển message.

### Step 7 — VERIFY
Bạn nhận `verify-report.md` từ Chủ thầu. Đọc `OVERALL STATUS`:
- `READY` — bạn được phép ship.
- `NEEDS_FIXES` — bạn yêu cầu Chủ thầu sinh TIP refine.
- `MAJOR_ISSUES` — bạn cân nhắc rollback hoặc quay lại Step 3.

### Step 8 — REFINE
Bạn chọn 1 trong các option Chủ thầu trình:

> Module X đã xong Y%.
> CẦN QUYẾT ĐỊNH: …
> Bạn muốn: [A] Ship as-is | [B] Fix … | [C] Fix cả … | [D] Custom

## What you must refuse to do

- **Tự code MQL5** hoặc tự sửa `.mq5` / `.mqh` trực tiếp. Đây là việc
  của Thợ. Nếu bạn thấy bug, bạn báo Chủ thầu sinh TIP fix.
- **Skip blueprint review.** Đừng reply "APPROVED" mà chưa đọc.
- **Đổi tech stack ở Step 6+.** Nếu bạn muốn đổi MT5 sang cTrader,
  bạn phải reject blueprint và quay lại Step 3.
- **Bypass permission gate.** Trong team/enterprise mode, không
  ship khi `mql5-permission` báo FAIL — kể cả bạn là Chủ nhà.

## How to use this prompt

Prompt này **không** dùng làm system message cho LLM. Đây là tài liệu
training cho **bạn** (Chủ nhà). Đọc 1 lần trước khi bắt đầu dự án mới
hoặc khi onboard người khác làm Chủ nhà cho dự án bạn đã thiết kế.

Khi paste prompt vào LLM, dùng `chu-thau.md` (cho Claude Chat) hoặc
`tho-thi-cong.md` (cho Claude Code).

---

# Homeowner — agent prompt (English mirror)

You are the **Homeowner** in the Triangle of Power of VIBECODE Kit /
vibecodekit-mql5-ea. You are the **only human** of the three actors —
the Contractor is Claude Chat (or an equivalent LLM), and the Builder is
Claude Code (or Devin / Cursor). You do not need to know MQL5,
MetaTrader, or broker APIs. You need to know **what you want** and
**what you refuse to accept**.

## Operating principles

1. **Decide, don't implement.** You say "I need a trend EA on EURUSD H1
   with 0.5% risk per trade", **not** "use ATR(14) with 1.5× ATR
   trailing stop". Technical detail is proposed by the Contractor and
   you approve or reject.
2. **Approval is a covenant.** When you reply "APPROVED" at the bottom
   of `step-4-blueprint.md` or "CONFIRM" at the bottom of `contract.md`,
   you are signing a covenant. Architecture **does not change** after
   that point unless you re-enter Step 3 (VISION).
3. **You are the bridge.** There is no direct chat protocol between
   Claude Chat and Claude Code. Every TIP travels down and every
   Completion Report travels up via your copy-paste.
4. **You are allowed to refuse.** If the Contractor proposes an
   architecture you do not understand, say "explain it in three
   sentences, each ≤ 15 words" instead of nodding.

## Step-by-step responsibilities

See the Vietnamese section above — the workflow is identical.

## What you must refuse to do

- **Write MQL5 yourself.** That is the Builder's job. If you spot a
  bug, report it to the Contractor for a refine TIP.
- **Skip blueprint review.** Do not reply "APPROVED" without reading.
- **Change tech stack at Step 6+.** Reject the blueprint and restart
  Step 3 if you want a different broker stack.
- **Bypass the permission gate.** In team/enterprise mode, never ship
  while `mql5-permission` returns FAIL — homeowner is not above the
  gate.
