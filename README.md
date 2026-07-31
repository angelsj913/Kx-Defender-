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
