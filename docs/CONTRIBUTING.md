# Contributing

Keep changes scoped, preserve simulation-first safety rules, and add a regression test for every bug fix.

Before submitting a change:

```powershell
npm test
npm pack --dry-run
```

Target `main` and describe the behavior change, verification results, and remaining risks.
