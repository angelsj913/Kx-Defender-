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
passwd admin <new-password>
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
