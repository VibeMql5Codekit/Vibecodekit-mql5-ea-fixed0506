# EA-bug golden dataset (Wave 3 W3.B)

This folder contains 20 deliberately buggy MQL5 Expert Advisors, each
isolated in its own folder and paired with an `expected.json` manifest
that pins the anti-pattern code(s) the kit's linters MUST emit.

The dataset is the contract the lint detectors are tested against. If
you change a detector, you change its golden fixture too — never the
other way round.

## Layout

```
tests/fixtures/ea-bugs/
  ap_NN_<slug>/
    EA.mq5         # buggy source (≤ 30 LOC, single-bug isolated)
    expected.json  # which AP code(s) lint MUST emit, plus must-not list
```

`expected.json` schema (every field optional except `primary_code` +
`must_contain`):

```json
{
  "primary_code": "AP-1",
  "must_contain": ["AP-1"],
  "must_not_contain": [],
  "description": "Bare CTrade.Buy with no stop-loss arg.",
  "severity": "ERROR"
}
```

`must_contain` is a strict subset check — every listed code MUST appear
among the lint findings. `must_not_contain` is a strict exclusion. Both
sides ignore the order and count of findings, so a fixture can attract
incidental detectors (e.g. AP-21 missing-meta on every EA that omits
the `// digits-tested:` comment) without flapping the test.

## Coverage

The 20 fixtures cover every detector currently emitted by `mql5-lint`
(8 critical + 12 best-practice). Method-hiding (`mql5-method-hiding-
check`) is intentionally excluded — it requires a real
`Include/*.mqh` compile pass, so its fixtures live separately under
`Include/*.mqh` + `tests/gates/phase-A/test_method_hiding.py`.

| AP   | Severity | Slug                       | Detector source                       |
|------|----------|----------------------------|---------------------------------------|
| AP-1 | ERROR    | ap_01_no_sl                | `lint.detect_ap1`                     |
| AP-2 | WARN     | ap_02_sl_too_tight         | `lint_best_practice.detect_ap2`       |
| AP-3 | ERROR    | ap_03_lot_fixed            | `lint.detect_ap3`                     |
| AP-4 | WARN     | ap_04_martingale_no_cap    | `lint_best_practice.detect_ap4`       |
| AP-5 | ERROR    | ap_05_too_many_inputs      | `lint.detect_ap5`                     |
| AP-7 | WARN     | ap_07_hardcoded_magic      | `lint_best_practice.detect_ap7`       |
| AP-8 | WARN     | ap_08_no_spread_guard      | `lint_best_practice.detect_ap8`       |
| AP-10| WARN     | ap_10_ordersend_no_check   | `lint_best_practice.detect_ap10`      |
| AP-11| WARN     | ap_11_mode_blind           | `lint_best_practice.detect_ap11`      |
| AP-12| WARN     | ap_12_leak_handle          | `lint_best_practice.detect_ap12`      |
| AP-13| WARN     | ap_13_broker_coupled       | `lint_best_practice.detect_ap13`      |
| AP-14| WARN     | ap_14_no_mfe_mae           | `lint_best_practice.detect_ap14`      |
| AP-15| ERROR    | ap_15_raw_ordersend        | `lint.detect_ap15`                    |
| AP-17| ERROR    | ap_17_webrequest_in_ontick | `lint.detect_ap17`                    |
| AP-18| ERROR    | ap_18_async_no_handler     | `lint.detect_ap18`                    |
| AP-20| ERROR    | ap_20_hardcoded_pip        | `lint.detect_ap20`                    |
| AP-21| WARN     | ap_21_one_digit_class      | `lint.detect_ap21`                    |
| AP-23| WARN     | ap_23_ctrade_no_retcode    | `lint_best_practice.detect_ap23`      |
| AP-24| WARN     | ap_24_history_unsynced     | `lint_best_practice.detect_ap24`      |
| AP-25| WARN     | ap_25_raw_delete           | `lint_best_practice.detect_ap25`      |

The driver test lives at
`tests/gates/phase-A/test_ea_bugs_golden_dataset.py`. It iterates every
folder and verifies `expected.json` against `mql5-lint --json` output.
