---
id: 54-stl-cheatsheet
title: MQL5 stdlib cheatsheet
tags: [stdlib, stl]
applicable_phase: A
---

# MQL5 stdlib cheatsheet

The MetaQuotes Standard Library lives under
`MQL5/Include/`.  Cheat-sheet of classes the kit relies on:

| Class           | Use                                                |
|-----------------|----------------------------------------------------|
| `CTrade`        | Order send/modify/close wrapper                    |
| `CPositionInfo` | Read position properties from terminal cache       |
| `COrderInfo`    | Read pending order properties                      |
| `CDealInfo`     | Read historical deal properties                    |
| `CSymbolInfo`   | Per-symbol contract spec                           |
| `CHashMap`      | Generic hash map                                   |
| `CArray`        | Generic dynamic array                              |
| `CExpert`       | Wizard-composable EA base class                    |

See reference 66 for `CTrade`/`CPositionInfo` deep dive and reference
60 for the wizard `CExpert`.
