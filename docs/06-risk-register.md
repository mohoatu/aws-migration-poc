# Risk register

| # | Risk | Likelihood | Impact | Owner | Mitigation |
|---|---|---|---|---|---|
| 1 | Migrated job produces different money, undetected | Medium | **Severe** | migration lead | Field-level gate on every parallel run; integers and status codes get no tolerance |
| 2 | Parallel run never sees month-end behaviour | **High** | Severe | migration lead | Parallel run must span a month-end close before cutover |
| 3 | Rounding differences accepted by engineering instead of finance | Medium | High | finance domain owner | Tolerance sheet signed before testing; gate separates the classes so they cannot be waved through together |
| 4 | Upstream feed changes format mid-programme | Low | High | platform owner | Schema declared in `schema.json`; a format change fails the parse loudly rather than producing silent nonsense |
| 5 | Downstream consumer hard-codes the old path | **High** | Medium | migration lead | Legacy path kept readable for one billing cycle; consumers notified and acknowledgement tracked |
| 6 | Cutover window overruns | Medium | Medium | platform owner | Rollback triggers are time-based, not judgement-based |
| 7 | Legacy server decommissioned too early | Low | **Severe** | platform owner | Decommission only after one clean month-end, in writing |
| 8 | Comparator itself is wrong | Low | Severe | migration lead | Comparator carries its own mutation suite — the tests are tested; see its repo |
| 9 | Key person leaves mid-programme | Medium | High | sponsor | Runbook, criteria and schema are written down; that is what this folder is |

## The two worth escalating

**Risk 2** is the one most migrations get wrong. A parallel run over ordinary
Tuesdays proves very little: month-end is where the period logic, the close
cycle and the largest volumes live. A programme that cuts over without crossing
a month-end has tested the easy case and called it done.

**Risk 1** is the one the whole design exists to address, and it is also the
one that *feels* handled long before it is. A clean run on ordinary data is
weak evidence. That is why criterion 1 asks for ten consecutive runs rather
than one, and why risk 8 exists at all: a check nobody has tried to break is
not a check.
