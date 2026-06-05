# Chat-driven EA build (Devin playbook)

The `mql5-spec-from-prompt` CLI bridges natural-language EA requests and the
`mql5-auto-build` pipeline. Combined with a Devin playbook, a one-line chat
message turns into a draft pull request containing a freshly scaffolded EA
that has already passed lint, compile, and the permission gate.

## End-to-end flow

```
user chat ──► Devin playbook ──► mql5-spec-from-prompt ──► ea-spec.yaml
                                                              │
                                                              ▼
                                                  mql5-auto-build
                                                  ├─ scan
                                                  ├─ build
                                                  ├─ lint
                                                  ├─ compile (Wine + MetaEditor)
                                                  ├─ permission-gate
                                                  └─ dashboard (publish quality matrix)
                                                              │
                                                              ▼
                                                  git commit + push + PR
                                                              +
                                                  dashboard public URL in PR body
```

## Local invocation

```bash
# 1) Translate prompt → spec
mql5-spec-from-prompt \
    "build EA trend EURUSD H1 risk 0.5% SL 30 TP 60 macd or sar" \
    --out /tmp/ea-spec.yaml --explain

# 2) Run the pipeline against that spec
mql5-auto-build --spec /tmp/ea-spec.yaml --out-dir /tmp/MyEA

# 3) Inspect the report (stages + dashboard URL)
jq '{ok, stages: [.stages[] | {name, ok}], dashboard}' \
    /tmp/MyEA/auto-build-report.json
```

The first command writes a schema-valid `ea-spec.yaml` to stdout (or to
`--out PATH`). Use `--explain` to see which fields came from the prompt
and which fell back to defaults, and `--strict` to require every
schema-mandatory field be inferable.

## What the parser understands

The parser is deterministic and regex-driven (no LLM call) — anything it
can't recognise falls back to a documented default instead of being
guessed at.

| Hint | Recogniser | Default |
|---|---|---|
| **Preset** | `trend`, `mean-reversion`, `breakout`, `scalping`, `hft`, `news`, `arbitrage`, `grid`, `dca`, `hedging-multi`, `ml-onnx` / `onnx`, `llm`, `service`, `portfolio-basket`, `wizard`, `stdlib` | `stdlib` |
| **Stack** | `netting`, `hedging`, `python-bridge`, `cloud-api`, `self-hosted-ollama`, `embedded-onnx-llm`, `standalone` (clamped to the preset's supported list) | preset's default |
| **Symbol** | All 14 FX majors, `XAUUSD`/`XAGUSD`, `BTCUSD`/`ETHUSD`, `US30`/`NAS100`/`GER40`/etc., and `EUR/USD` slash form | `EURUSD` |
| **Timeframe** | `M1`–`M30`, `H1`–`H12`, `D1`, `W1`, `MN1` | `H1` |
| **Risk** | `risk 0.5%`, `0.5% risk`, `daily loss 5%`, `SL 30 pips`, `TP 60`, `max spread 2`, `max positions 5` | schema defaults |
| **Signals** | `macd`, `sar`, `rsi`, `ema_cross`, `bbands`, `atr_break`; logic = `OR` if the prompt contains "or", else `AND` | omitted |
| **Name** | `named MyEA` / `called Foo` | `PresetSymbolTimeframe` |

## Sample prompts

These are the seed prompts the Devin playbook is expected to handle. Each
one produces a schema-valid spec that the orchestrator accepts.

* `build EA trend EURUSD H1 risk 0.5%`
* `scalping XAUUSD M5 risk 1% SL 30 TP 60 macd or rsi`
* `mean-reversion USDJPY H4 daily loss 5%`
* `breakout GBPUSD M15 SL 50 TP 100 sar or rsi bbands`
* `ml-onnx EURUSD H1 risk 0.3% python-bridge`
* `service llm bridge ollama` *(self-hosted LLM service)*
* `stdlib named MyEA` *(everything else defaulted)*

## Suggested playbook macro

When wiring this into a Devin playbook, attach a macro like `!build_ea`
so chat users can fire the workflow with a single command:

```
!build_ea trend EURUSD H1 risk 0.5%
```

The playbook should:

1. Run `mql5-spec-from-prompt "$ARGS" --out ea-spec.yaml --strict`.
2. Run `mql5-auto-build --spec ea-spec.yaml --out-dir build/$EA_NAME --force`.
3. Read `build/$EA_NAME/auto-build-report.json`; surface `.ok`, any failing
   stage's `detail`, and the `.dashboard.public_url` back to the user.
4. If `.ok` is true, open a draft PR with the scaffold under
   `build/<EA_NAME>/` and include the dashboard URL in the PR body.

`mql5-auto-build` already emits an idempotent report under `out_dir`, so
the playbook can re-run the same prompt and the pipeline stays
deterministic.

## Dashboard URL hook

The last stage of `mql5-auto-build` renders the 64-cell RRI quality
matrix to `<out_dir>/quality-matrix.html`. The pipeline always writes
that file; if a publish command is configured the report also includes
a public URL.

The publish command is resolved in this order:

1. `--publish-cmd <cmd>` flag on `mql5-auto-build` (or `mql5-dashboard`).
2. `$MQL5_DASHBOARD_PUBLISH_CMD` environment variable.
3. Nothing → the report exposes a `file://` URL only.

The command is invoked as `<cmd> <html_path>`; whatever it prints on the
**last non-blank stdout line** becomes `dashboard.public_url`. Examples:

```bash
# Devin org blueprint (initialize block):
echo 'MQL5_DASHBOARD_PUBLISH_CMD=vercel deploy --prod' >> $ENVRC

# Or a shell wrapper around `aws s3 cp`:
cat > /usr/local/bin/mql5-publish-s3 <<'EOF'
#!/bin/bash
KEY="dashboards/$(date +%s)-$(basename $1)"
aws s3 cp "$1" "s3://my-bucket/$KEY" --content-type text/html
echo "https://my-bucket.s3.amazonaws.com/$KEY"
EOF
chmod +x /usr/local/bin/mql5-publish-s3
export MQL5_DASHBOARD_PUBLISH_CMD=mql5-publish-s3
```

If the publish command exits non-zero or is missing, the dashboard
stage degrades gracefully: the local HTML is still written, the report
records `.dashboard.error`, and the overall pipeline status is
unchanged. A broken publish hook never turns a green build red.
