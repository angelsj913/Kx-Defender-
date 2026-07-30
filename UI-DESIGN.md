# Kx-Defender UI/Frontend Design Specification

## Design Philosophy

1. **Single UI Instance**: One dashboard that persists across commands
2. **Reactive Updates**: Commands update the dashboard in-place without full regeneration
3. **Responsive Layout**: Auto-fills screen real estate at any resolution
4. **Command-Centric**: Primary interaction is command input, not mouse clicks
5. **Status Awareness**: Real-time feedback on command execution
6. **Minimal Overhead**: Dashboard memory footprint should remain constant

## Dashboard Layout

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ 🛡️  Kx-Defender                                          [lang] [help] [clear] │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ COMMAND PALETTE                                                          │  │
│  │ ───────────────────────────────────────────────────────────────────────  │  │
│  │ kx roast tickets --scope lab --sim                         [📤 Execute]  │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ EXECUTION STATUS                                                         │  │
│  │ ───────────────────────────────────────────────────────────────────────  │  │
│  │ Status: ✓ OK                Mode: Simulate               Scope: lab      │  │
│  │ Module: performing-kerberoasting-attack                                  │  │
│  │ Duration: 145ms            Findings: 1                   Artifacts: 2    │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌────────────────────────────────────┬─────────────────────────────────────┐  │
│  │ FINDINGS (1)                       │ ARTIFACTS                           │  │
│  │ ───────────────────────────────────┼─────────────────────────────────────│  │
│  │ 🔴 HIGH: SPN enumeration complete  │ 📁 spns (Array[2])                 │  │
│  │ Found 2 SPN(s) in lab.local        │   ├─ HTTP/web.lab.local            │  │
│  │                                    │   └─ MSSQLSvc/db.lab.local:1433    │  │
│  │ Evidence:                          │                                     │  │
│  │   • count: 2                       │ 📁 tgs_hashes (Array[2])           │  │
│  │                                    │   ├─ krb5tgs hash 1                │  │
│  │ 📍 Evidence View ↓                 │   └─ krb5tgs hash 2                │  │
│  │                                    │                                     │  │
│  │                                    │ 📌 Metadata                         │  │
│  │                                    │   • module: kerberoasting          │  │
│  │                                    │   • engine: self-built             │  │
│  └────────────────────────────────────┴─────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ HISTORY                                                    [View All →]  │  │
│  │ ───────────────────────────────────────────────────────────────────────  │  │
│  │ 14:32:15 ✓ kx roast tickets --scope lab --sim            (145ms)       │  │
│  │ 14:31:22 ✓ kx watch procs --scope lab --sim              (523ms)       │  │
│  │ 14:30:45 ✓ kx sweep web --scope lab --sim --url http://... (2.1s)     │  │
│  │ 14:29:10 ⚠ kx sig scan --scope lab --sim --path /notfound (89ms)      │  │
│  │ 14:28:32 ✗ kx kill pid --scope lab --sim --pid 9999     (error)       │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ HELP / QUICK REFERENCE                                     [Full Docs →] │  │
│  │ ───────────────────────────────────────────────────────────────────────  │  │
│  │ Usage: kx <VERB> <OBJECT> [--flags]                                     │  │
│  │                                                                           │  │
│  │ Common verbs:                                                            │  │
│  │   roast, relay, loot, watch, kill, sig, sweep, nexus, audit             │  │
│  │                                                                           │  │
│  │ Flags: --scope lab|owned|pact  --sim (default) | --live  --url, --pid   │  │
│  │                                                                           │  │
│  │ Examples:                                                                │  │
│  │   kx roast tickets --scope lab        (Kerberoasting simulation)        │  │
│  │   kx watch procs --scope lab --sim    (Process monitoring)              │  │
│  │   kx sweep web --scope lab --url localhost:8080  (Web scanner)          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Component Specifications

### 1. Command Palette (Top Section)

**Purpose**: Input area for kx commands

**State Variables**:
- `commandText: string` - Current command being typed
- `commandHistory: string[]` - List of previously executed commands
- `historyIndex: number` - Current position in history (arrow key navigation)

**Behavior**:
- Real-time validation as user types
- Arrow UP/DOWN for command history navigation
- Tab completion for verbs/objects
- Auto-suggest based on lexicon
- Submit on Enter key

**Updates**:
- Never cleared when new command executes
- User can modify and re-execute
- Maintains state across multiple commands

### 2. Execution Status Panel (Upper-Right)

**Purpose**: Quick status and metadata about current command

**Display Fields**:
```
Status: [✓ OK | ⚠ ERROR | ✗ DENIED | ⏳ RUNNING]
Mode: [Simulate | Execute]
Scope: [lab | owned | pact | engagement]
Module: [Full module name]
Duration: [XXXms or XXs]
Findings: [N] | Artifacts: [N]
```

**Real-Time Updates**:
- Status changes as command executes: RUNNING → OK/ERROR/DENIED
- Duration updates every 100ms during execution
- Finding/artifact counts updated when result completes

**Animations**:
- Status icon pulse during execution
- Color transitions: gray (RUNNING) → green (OK) → red (ERROR)

### 3. Findings Panel (Left Section)

**Purpose**: Display security findings from module execution

**Structure**:
```
Finding Card
├─ Icon (severity indicator: 🔴🟠🟡🟢)
├─ Title
├─ Severity badge
├─ Detail text
├─ Evidence section
└─ Expand/collapse arrow
```

**Features**:
- Expandable evidence with JSON/tree view
- Searchable findings list
- Filter by severity
- Copy finding to clipboard

**Reactive Updates**:
- New findings appear as module completes
- No list regeneration; items inserted/updated
- Smooth scroll to latest finding

### 4. Artifacts Panel (Right Section)

**Purpose**: Display generated data from module execution

**Structure**:
```
Artifact Group
├─ Name (e.g., "spns", "tgs_hashes")
├─ Type indicator (Array, Object, String, etc)
├─ Count/size
├─ Preview (first 3 items or first 100 chars)
└─ Expand to view full data
```

**Display Modes**:
- **Compact**: Name, type, count only
- **Preview**: Shows first few entries
- **Expanded**: Full content in JSON/table format

**User Actions**:
- Export to JSON/CSV
- Copy to clipboard
- Raw view toggle (JSON vs. formatted)

### 5. History Panel (Bottom-Left)

**Purpose**: List of recent command executions

**Entry Format**:
```
[HH:MM:SS] [✓/⚠/✗] [Command] ([Duration])
```

**Features**:
- Clickable to view that command's results
- Color-coded by status (green/orange/red)
- Sortable by time, status, or duration
- Clear history button

**Reactive Updates**:
- New entries appear at top
- Existing entries don't shift/regenerate
- Maintains scroll position

### 6. Help Panel (Bottom-Right)

**Purpose**: Contextual help and quick reference

**Sections**:
- **Usage**: kx <VERB> <OBJECT> [--flags]
- **Common Verbs**: roast, relay, loot, watch, kill, sig, sweep, nexus, audit
- **Available Flags**: --scope, --sim/--live, --url, --pid, --at, --realm, --bind
- **Examples**: Context-aware based on last command typed

**Dynamic Content**:
- Help updates when user types verb
- Shows available objects for selected verb
- Highlights relevant flags for command

---

## State Management Architecture

### Data Structure

```typescript
interface DashboardState {
  // Current command
  commandInput: string
  commandHistory: string[]
  historyIndex: number
  
  // Latest execution
  latestResult: ModuleResult | null
  executionStatus: 'idle' | 'running' | 'completed' | 'error'
  executionStartTime: number
  executionDuration: number
  
  // UI Panels
  findingsExpanded: Set<string>  // Expanded finding IDs
  artifactsExpanded: Set<string> // Expanded artifact names
  historyFilter: 'all' | 'success' | 'error'
  helpContext: string            // Current verb/object for help
  
  // Settings
  theme: 'dark' | 'light'
  language: 'en' | 'ko'
  resultsPerPage: number
}
```

### Update Flow

```
User Types Command
  ↓
Command Input Event
  ├─ Validate syntax (partial)
  ├─ Update helpContext
  ├─ Trigger auto-suggest
  └─ Render updated help panel
  
User Presses Enter
  ↓
Send Command to Backend
  ├─ executionStatus = 'running'
  ├─ executionStartTime = now()
  ├─ Start timer for duration display
  └─ Render status as "RUNNING" with spinner
  
Backend Processes Command
  ↓ (every 100ms)
Update Duration Display
  └─ executionDuration = elapsed time
  
Backend Returns Result
  ↓
Update Latest Result
  ├─ latestResult = result
  ├─ executionStatus = 'completed' | 'error' | 'denied'
  ├─ commandHistory.push(command)
  ├─ Render findings (as they appear)
  ├─ Render artifacts (as they appear)
  └─ Add entry to history panel
```

### Critical Rule

**No DOM Regeneration on Command Execution**

When results arrive:
```javascript
// ✗ WRONG - regenerates entire findings list
results.findings.forEach(f => {
  findingsPanel.innerHTML += renderFinding(f);
});

// ✓ CORRECT - appends new findings
results.findings.forEach(f => {
  const element = renderFinding(f);
  findingsPanel.appendChild(element);
  animate(element, 'slideIn');
});
```

---

## Responsive Design

### Mobile (< 768px)
```
┌──────────────────────────┐
│ Command                  │
├──────────────────────────┤
│ Status                   │
├──────────────────────────┤
│ Findings                 │
│ (stacked)                │
├──────────────────────────┤
│ Artifacts                │
│ (expandable tabs)        │
├──────────────────────────┤
│ History                  │
└──────────────────────────┘
```

### Tablet (768px - 1024px)
```
┌─────────────────────────────────────┐
│ Command                             │
├─────────────────────────────────────┤
│ Status                              │
├──────────────────┬──────────────────┤
│ Findings         │ Artifacts        │
│                  │                  │
├──────────────────┴──────────────────┤
│ History                             │
└─────────────────────────────────────┘
```

### Desktop (> 1024px)
```
┌────────────────────────────────────────────────────┐
│ Command Palette                                    │
├─────────────┬──────────────────────────────────────┤
│ Status      │ Help/Reference                       │
├─────────────┴──────────────────────────────────────┤
│ Findings (50%) │ Artifacts (50%)                  │
├─────────────────────────────────────────────────────┤
│ History                                            │
└─────────────────────────────────────────────────────┘
```

### Scaling Rules
- Panels use CSS Grid with `auto` columns
- Font sizes scale with viewport width
- Padding/margins scale proportionally
- Max-width constraint: 1600px

---

## Color Scheme

### Dark Theme (Primary)
```
Background:     #0f1419  (Deep gray-blue)
Primary Text:   #e8eaed  (Off-white)
Secondary Text: #9aa0a6  (Medium gray)
Accent:         #8ab4f8  (Blue)

Status Colors:
  Running:  #fbc02d  (Amber)
  OK:       #81c995  (Green)
  Error:    #f28482  (Red)
  Denied:   #f6a1b2  (Pink)

Severity:
  Critical: #d32f2f  (Red)
  High:     #f57c00  (Orange)
  Medium:   #fbc02d  (Amber)
  Info:     #0288d1  (Blue)
```

### Light Theme (Alternative)
```
Background:     #ffffff  (White)
Primary Text:   #202124  (Black)
Secondary Text: #5f6368  (Gray)
Accent:         #1f73e7  (Blue)

Status Colors:
  Running:  #f57f17  (Amber)
  OK:       #2e7d32  (Green)
  Error:    #c62828  (Red)
  Denied:   #c2185b  (Pink)
```

---

## Animation & Transitions

### Entry Animations (200ms)
```
Finding appears:    Slide in from left + fade
Artifact expands:   Height animation + fade
History entry:      Slide in from top + highlight pulse
```

### Duration Display
```
Increments: Every 100ms
Format: Real-time counter showing elapsed time
Example: 145ms, 1.2s, 2.15s
```

### Status Transitions
```
IDLE      → RUNNING    (0ms, immediate)
RUNNING   → OK/ERROR   (300ms, color fade)
OK/ERROR  → persistence (stays visible)
```

---

## Performance Targets

**Memory**:
- Base dashboard: < 50MB
- Per command result: < 10MB
- History retention: Last 100 commands (5MB max)

**Rendering**:
- Initial load: < 1s
- Command input response: < 16ms (60fps)
- Result panel update: < 100ms
- Scroll performance: 60fps maintained

**Network**:
- Command submission: < 50ms latency
- Result streaming: Chunked for large artifacts
- WebSocket connection: Persistent for real-time updates

---

## Command Completion & Suggestions

### Auto-Completion Levels

1. **Verb Completion** (70+ available)
   ```
   kx ro[TAB] → kx roast
   kx w[TAB]  → kx watch / kx wifi (shows options)
   ```

2. **Object Completion**
   ```
   kx roast [TAB] → kx roast tickets / kx roast spn
   ```

3. **Flag Completion**
   ```
   kx roast tickets --[TAB] → Shows available flags
   --scope → shows [lab|owned|pact|engagement]
   --mode → shows [simulate|execute]
   ```

4. **Context Awareness**
   ```
   kx roast --url [TAB]      → Not applicable (no URL param)
   kx sweep web --url [TAB]  → Previous URLs from history
   kx kill --pid [TAB]       → Suggestions from previous --pid values
   ```

### Smart Suggestions
- Learn from command history
- Suggest previously used scope when applicable
- Remember last used mode (--sim vs --live)
- Autocomplete target domains/hosts from previous commands

---

## Error Handling & Feedback

### Input Validation (Pre-Submit)
```
❌ "kx invalid" → Red underline, "Unknown verb 'invalid'"
⚠️  "kx roast" → Orange underline, "Missing object, try: tickets, spn"
✓  "kx roast tickets" → Green checkmark, ready to submit
```

### Execution Errors
```
Status panel shows:
  Status: ✗ ERROR
  Error message in tooltip
  Full error details in artifacts panel

History shows error badge:
  14:32:15 ✗ kx kill --pid 9999 (permission denied)
```

### No Result Errors
```
No Findings:
  → Display: "No findings generated"
  → Details: "Scan completed without matches"

No Artifacts:
  → Display: "No artifacts collected"
  → Reason: "Simulation mode or no data"
```

---

## Accessibility Features

- Keyboard navigation (Tab, Shift+Tab, Arrow Keys, Enter)
- ARIA labels for screen readers
- High contrast mode support
- Font size adjustment (100% - 150%)
- Command history with keyboard shortcuts (Ctrl+P for previous)

---

## Implementation Roadmap

### Phase 1: MVP Dashboard
- ✓ Command palette with input validation
- ✓ Status panel with real-time updates
- ✓ Findings/artifacts display
- ✓ Basic history

### Phase 2: Enhancements
- Auto-completion with verb/object suggestions
- Responsive mobile layout
- Theme toggle
- Export functionality

### Phase 3: Advanced Features
- Batch command playbooks
- Result filtering and search
- Custom dashboard layouts
- Real-time WebSocket updates
- Analytics dashboard

---

## Testing Checklist

- [ ] Single UI instance persists across 50+ commands
- [ ] No memory leaks with extended use
- [ ] Findings update without full list regeneration
- [ ] Mobile layout responsive at all breakpoints
- [ ] Command history maintains state
- [ ] 60fps animations maintained
- [ ] Auto-completion suggestions accurate
- [ ] Keyboard navigation works fully
- [ ] Light/dark themes consistent
