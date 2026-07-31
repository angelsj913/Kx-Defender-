# Kx-Defender

Kx-Defender is a Windows-friendly terminal security lab with the KxLang command interface, local orchestration, and built-in attack/defense simulations.

The interface starts in English. Run `lang ko` after login to switch to Korean; the choice is saved for later sessions.

## Install and start

PowerShell:

```powershell
npx -y --prefer-online github:angelsj913/Kx-Defender-
```

The first fresh installation creates this local operator account:

```text
username: admin
password: admin
```

Change the password after login:

```text
kx security password        Change the admin password without exposing it
kx security status          Check account and configuration security
kx setup wizard             Configure language and admin password
```

Kx-Defender stores its local runtime and settings under `%USERPROFILE%\.kx-defender`. If Python is unavailable, setup downloads a portable Python runtime once.

## Everyday commands

```text
/h                         Show help
kx doctor                  Diagnose the local installation
sentry                     Run the default local detection simulation
watch procs --scope lab --sim
sig scan --scope lab --sim
daemon status              Show background watcher status
alert list --status new    List unhandled local alerts
case list                  List local incident cases
lang ko                    Switch to Korean
lang en                    Switch to English
update                     Update from main
exit                       Close the client
```

Human-readable output is the interactive default. Use the one-shot CLI without `--pretty` when stable JSON is needed:

```powershell
kx sentry
kx --pretty sentry
```

## Update

Inside the client, run:

```text
update
```

Or from PowerShell:

```powershell
npx -y --prefer-online github:angelsj913/Kx-Defender- update
```

Updates are prepared and tested in a separate release directory before activation:

```powershell
kx update check
kx update apply
kx update status
kx update rollback
```

The current release remains active when download, setup, or smoke testing fails.

## Alerts and cases

Alerts keep a stable local ID, deduplicate repeated findings, and retain every
status change in `%USERPROFILE%\.kx-defender\operator.db`. The existing
`alerts.jsonl` file remains as a compatibility log.

```powershell
kx alert migrate
kx alert list --status new --severity high
kx alert show ALT-...
kx alert ack ALT-... --note "investigating"
kx alert resolve ALT-... --reason "benign"
kx alert reopen ALT-...

kx case create --from-alert ALT-... --title "Process investigation"
kx case add CASE-... ALT-...
kx case note CASE-... "Collected process tree"
kx case close CASE-... --resolution "contained"
```

Add `--json` to alert and case commands for stable automation output.

## Evidence bundles

Export a run or case into an integrity-checked local bundle. `standard`
redaction masks secret-bearing fields; `strict` also anonymizes usernames,
user-home paths, and IP addresses. Binary artifacts are excluded instead of
being copied without redaction.

```powershell
kx evidence export --case CASE-... --to incident.kxev --redact strict
kx evidence export --run RUN-ID --to run.kxev
kx evidence inspect incident.kxev
kx evidence verify incident.kxev
kx evidence import incident.kxev --read-only
```

Import verifies all hashes and archive paths before writing anything, then
stores the extracted copy as read-only under `.kx-defender\evidence\imported`.

## Command history and favorites

The interactive client provides Tab completion from the KxLang lexicon and
restores the latest 100 commands for arrow-key navigation. Up to 500 commands
are kept locally. Password-changing commands are never stored; secret flags
are saved only as `<redacted>`.

```powershell
kx history list
kx history search sentry
kx history clear --yes
kx favorite add daily-check "sentry --scope lab --sim"
kx favorite list
kx favorite run daily-check
```

Favorites containing credentials are rejected. A favorite containing `--live`
requires `kx favorite run <name> --confirm-live`.

## KxSig rule workbench

Validate and test user rules before enabling them. User rules and enable/disable
state live under `.kx-defender\rules\kxsig`, so application updates do not
overwrite them.

```powershell
kx sig validate .\custom-rules.json
kx sig test .\custom-rules.json --sample .\sample.txt
kx sig import .\custom-rules.json
kx sig show CUSTOM-001
kx sig disable CUSTOM-001 --reason "too noisy"
kx sig enable CUSTOM-001
kx sig conflicts
kx sig quarantine .\unsafe-rules.json
```

Rule tests run in a separate process with a three-second timeout. Duplicate
IDs, unsupported metadata, nested regex quantifiers, oversized rules, and
oversized samples are rejected.

## Baselines and drift

Capture a local system baseline, then explain what changed. The default
snapshot records process metadata, runtime versions, and hashes of Kx
configuration and user-rule files. Add `--path` only for a directory you
explicitly want to monitor.

```powershell
kx baseline create workstation-clean
kx baseline create project-clean --path .\project
kx baseline list
kx baseline compare workstation-clean
kx baseline show workstation-clean
kx baseline delete workstation-clean
```

Baseline files contain hashes and metadata, not passwords or watched-file
contents. Symbolic links, more than 5,000 files, and hashing files larger than
50 MiB are rejected or skipped safely.

## Playbooks and schedules

Playbooks are JSON v1 files containing up to 20 validated KxLang steps:

```json
{
  "name": "daily-local-check",
  "version": 1,
  "steps": [
    {"run": ["sentry", "--scope", "lab", "--sim"], "timeout": 60},
    {"run": ["watch", "procs", "--scope", "lab", "--sim"]}
  ],
  "on_error": "stop"
}
```

```powershell
kx playbook validate .\daily.json
kx playbook run .\daily.json --dry-run
kx playbook run .\daily.json
kx schedule add daily-check --playbook .\daily.json --daily 09:00
kx schedule list
kx schedule disable daily-check
kx schedule enable daily-check
```

Steps run sequentially with per-step timeouts and a single-run lock. Meta
commands cannot appear in playbooks. Live steps require both
`"allow_live": true` in the file and `--confirm-live` at execution, and live
playbooks cannot be scheduled. The existing daemon checks due schedules after
each watcher tick; no OS task or external service is installed.

## Operations dashboard

The interactive client opens on a read-only operational overview. Use number
keys `1` through `6`, or the section names, to switch between Overview, Alerts,
Runs, Cases, Rules, and Health. The layout uses compact labels in narrow
PowerShell windows and redraws when the terminal size changes.

The same bounded snapshots are available without the interactive client:

```powershell
kx dashboard overview
kx dashboard alerts
kx dashboard runs --json
kx dashboard cases
kx dashboard rules
kx dashboard health
```

Run history and alert/case state share the persistent
`$HOME\.kx-defender\operator.db`, so an atomic application update does not
discard or split operational history.

## Safety model

- Simulation is the default mode.
- Live execution requires an authorized scope.
- Only lab, owned, engagement-approved, localhost, RFC1918, `.lab`, `.local`, and `.test` targets are allowed where applicable.
- Credentials and live service data are not bundled.

## Troubleshooting

If the `kx` command is not available in the current PowerShell session, run:

```powershell
$env:PATH="$env:LOCALAPPDATA\Kx-Defender\bin;$env:PATH"
kx
```

If setup was interrupted, start the `npx` command again. The installer reuses completed local components.

Diagnose the installation without changing files:

```powershell
kx doctor
kx doctor --verbose
kx doctor --json
```

Repairs are opt-in and preserve a backup where applicable:

```powershell
kx doctor --repair config
kx doctor --repair path,shims,venv
```

## Development

```powershell
git clone https://github.com/angelsj913/Kx-Defender-.git
cd Kx-Defender-
npm test
node scripts\npx-entry.js
```

The test command validates the terminal renderer, Windows process spawning, authentication, KxLang, and local modules.

More detail:

- [KxLang grammar](docs/kxlang.md)
- [Architecture](docs/architecture.md)
- [License](LICENSE)

Licensed under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
