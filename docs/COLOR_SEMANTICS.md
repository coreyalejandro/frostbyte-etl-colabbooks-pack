# Frostbyte Color Semantics

## Primary Palette

| Color | Hex | Usage |
|-------|-----|-------|
| **Accent (Amber)** | `#fbbf24` | Success, active, completed, primary actions |
| **Green** | `#4ade80` | Connected, live, healthy |
| **Red** | `#f87171` | Errors, failures, disconnected, offline |
| **Blue** | `#60a5fa` | Processing, running, in-progress |

## Semantic Meaning

### Status States

| State | Color | Example |
|-------|-------|---------|
| **Active / Live** | 🟡 Amber | `[ACTIVE]`, `LIVE` toggle |
| **Completed / Success** | 🟡 Amber | `✓ docling`, `0.99` score |
| **Processing** | 🔵 Blue | `⟳ nomic-embed`, `[EMBED]` label |
| **Failed / Error** | 🔴 Red | `✗ policy-classifier`, `FAILED: ...` |
| **Connected / Healthy** | 🟢 Green | `● STREAMING` badge |
| **Disconnected** | 🔴 Red | `✕ OFFLINE` badge |
| **Warning** | 🟠 Amber-400 | Log warnings (not errors) |

### Component Usage

#### Model Activity Events
```
● nomic-embed-text-v1 [EMBED]     ← Blue = processing
✓ docling v2.7.0 [PARSE]          ← Amber = completed
✗ policy-classifier [VERIFY]      ← Red = failed
```

#### Connection Status
```
┌─────────────┐  ┌─────────────┐
│ ●  LIVE  🟢 │  │ ○  PAUSED   │
│ (amber)     │  │ (gray)      │
└─────────────┘  └─────────────┘
     ↑                    ↑
  ON STATE            OFF STATE
  
STREAMING badge = Green (healthy)
ERROR badge = Red (disconnected)
```

#### Errors vs Warnings
```
Error (operation failed):   🔴 text-red-400
Warning (log level warn):   🟠 text-amber-400
```

## Implementation

### Tailwind Classes

```jsx
// Success / Completed / Active
<span className="text-accent">✓ Completed</span>
<span className="text-accent">[ACTIVE]</span>

// Errors / Failures
<span className="text-red-400">✗ Failed</span>
<span className="text-red-400">FAILED: Error message</span>

// Processing
<span className="text-blue-400">⟳ Processing</span>

// Connected / Healthy
<span className="text-green-400">● Connected</span>

// Warnings (logs only)
<span className="text-amber-400">⚠ Warning message</span>
```

## Common Mistakes to Avoid

❌ **DON'T**: Use `text-accent` for errors
```jsx
// WRONG
<p className="text-accent">FAILED: Something went wrong</p>

// RIGHT
<p className="text-red-400">FAILED: Something went wrong</p>
```

❌ **DON'T**: Use amber for disconnected states
```jsx
// WRONG
<span className="text-accent">DISCONNECTED</span>

// RIGHT
<span className="text-red-400">OFFLINE</span>
```

## Migration Guide

If you see amber/yellow used for errors, change to red:

```bash
# Find problematic uses
grep -r "text-accent" src/ | grep -i "fail\|error"

# Should return nothing (all errors should use text-red-400)
```

## Why This Matters

1. **Accessibility**: Color-blind users can distinguish red/green/blue/amber
2. **Intuition**: Red = bad, Green = good, Amber = caution/success, Blue = info/processing
3. **Consistency**: Same meaning across all components
