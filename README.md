# Kx-Defender

Self-built Windows-oriented attack + defense platform (KxLang). Authorized & lawful use only.

## Install

`npx kx-defender` needs the package on npmjs.com. Until the first publish you will see **E404**.

### Publish once (owner)

```powershell
npm login
git clone https://github.com/angelsj913/Kx-Defender-.git
cd Kx-Defender-
.\scripts\publish-npm.ps1
```

### Then

```bash
npx --yes kx-defender add --all -g
```

### Without npm publish

```powershell
git clone https://github.com/angelsj913/Kx-Defender-.git
cd Kx-Defender-
node scripts/npx-entry.js add --all -g
```

Do **not** use third-party `npx skills add …` for this repo.

License: Apache-2.0
