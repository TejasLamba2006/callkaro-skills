# Workbook spec

`python build_workbook.py qa.json out.xlsx`. Every key below is optional except `summary`. Scores, pass % and the Summary tab are live formulas, so testers editing Status, Passed or Score update the verdict. Spare rows are validated and formatted for cases added later.

## JSON

```json
{
  "summary": {"agent_name": "", "agent_id": "", "version_name": "", "version_id": "", "date": ""},
  "brief":  [{"section": "Business and goal", "detail": "..."}],
  "review": [{"area": "", "check": "", "score": 0, "good": "", "bad": "", "recommendation": "", "reference": ""}],
  "sim":    [{"id": "", "name": "", "category": "", "persona": "", "branch": "", "critical": "Y",
              "runs": 5, "passed": 5, "previous_pct": 0.8, "happened": "", "comment": "",
              "layer": "prompt", "batch_id": ""}],
  "manual": [{"id": "", "category": "", "persona": "", "branch": "", "say": "", "expected": "",
              "critical": "N", "status": "Not Run", "score": null, "comments": "", "layer": "", "call_id": ""}]
}
```

- `critical`: `Y` or `N`. `layer`: `prompt`, `function`, `config`, `voice/platform`, `data`, `none`. `status`: `Pass`, `Fail`, `Blocked`, `Not Run`.
- `previous_pct` is a fraction (0.8 = 80%), blank on the first QA.
- `category` is free text. Reuse the same spelling on a case across both tabs; each distinct category gets its own colour, listed with counts on Summary.

## Tabs

| Tab | Content |
|---|---|
| Summary | agent, version, date, Review %, Simulation %, QA score, critical cases at 5/5, verdict, manual passed/run, cases per category and chart |
| Agent Brief | the Stage 0 brief, one section per row |
| Agent Review | Area, Check, Score, Good, Bad, Recommendation, Reference |
| Simulation Results | Test id, name, Category, Persona, Branch, Critical, Runs, Passed, Pass %, Previous pass %, What happened, Comment, Layer, Batch id |
| Manual Test Cases | TC id, Category, Persona/setup, Branch, What to say, Expected behaviour (incl. how the call ends), Critical, Status, Score, Comments, Layer, Call id |

## Colour legend

- Header: dark slate, white bold text; header frozen, first column(s) frozen, autofilter on, text wrapped, banded rows.
- Category: one pastel fill per category.
- Critical = Y: red bold. Status: Pass green, Fail red, Blocked amber, Not Run grey.
- Scores (0-10) and Pass %: red below 6 (or 60%), amber to 8.5 (or 85%), green above.
- Verdict: green PASS or red FAIL (QA score at least 85 and every critical case with all runs passed).
