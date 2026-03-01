# allman

Sublime Text plugin sources for two complementary formatting commands:

- `allmanize`: converts opening braces to Allman style, reindents code, then applies an ordered custom replacement pass.
- `deallmanize`: performs the opposite flow, preserving PSR-12-style declaration braces in PHP files, then applies the reverse replacement pass in reverse order.

## Quick Start

## 1) Install in Sublime Text

Copy both plugin files into your Sublime Text `User` package:

- macOS: `~/Library/Application Support/Sublime Text/Packages/User/`

## 2) Bind keys

Use the repository keymap file `Default (OSX).sublime-keymap`, or paste the bindings below:

```json
[
    {
        "keys": ["ctrl+super+alt+a"],
        "command": "allmanize",
        "context": [
            {
                "key": "selector",
                "operator": "equal",
                "operand": "source.c, source.c++, source.js, source.php, source.objc, source.swift, source.java, source.rust"
            }
        ]
    },
    {
        "keys": ["ctrl+super+alt+d"],
        "command": "deallmanize",
        "context": [
            {
                "key": "selector",
                "operator": "equal",
                "operand": "source.c, source.c++, source.js, source.php, source.objc, source.swift, source.java, source.rust"
            }
        ]
    }
]
```

## 3) Reload plugin host

In Sublime Text:

- `Tools > Developer > Reload Plugin`

## Commands

## `allmanize`

Entry point: `AllmanizeCommand.run()`.

Pipeline order:

1. Split inline opening braces to Allman form (`... {` -> newline before `{`) where applicable.
2. Reindent by structural brace depth.
3. Apply the custom ordered replacement list as the last step.

Status message includes:

- number of brace lines split
- number of lines reindented
- number of ordered replacements applied

## `deallmanize`

Primary entry point: `DeallmanizeCommand.run()`.
Compatibility alias: `DeallmanizePhpCommand` (maps to command id `deallmanize_php`).

Pipeline order:

1. Collapse leading `{` lines onto previous lines where allowed.
2. Preserve Allman braces for PSR-12 declarations only in PHP scope (see below).
3. Reindent by structural brace depth.
4. Apply reverse replacements in reverse order as the last step.

Status message includes:

- number of brace lines collapsed
- number of preserved PSR-12 declaration braces
- number of lines reindented
- number of reverse replacements applied

## PSR-12 Preservation in `deallmanize`

When de-allmanizing, declaration braces remain Allman-style for:

- named functions
- classes (`class`, with optional `abstract`/`final`/`readonly`)
- `interface`
- `trait`
- `enum`

Anonymous classes are not treated as class declarations for this preservation check.

This heuristic is PHP-only. In non-PHP files, declaration-preservation is skipped.

## Protected Regions (Not Modified)

Both commands use a code-segment scanner and do not apply transformations inside:

- single-quoted strings `'...'`
- double-quoted strings `"..."`
- line comments `// ...`
- line comments `# ...`
- block comments `/* ... */` including multiline blocks

Important: the scanner tracks multiline block comment state across lines.

## Ordered Replacement Rules

These are applied exactly in order for `allmanize`, as final step.

1. `([^ \n]+) \(` -> `\1( `
2. `([^ \n]+)\)` -> `\1 )`
3. `\(\)` -> `()`
4. `\( \)` -> `()`
5. `([^ \n]+) \[` -> `\1] `
6. `([^ \n]+)\[` -> `\1 ]`
7. `\[\]` -> `[]`
8. `\[ \]` -> `[]`
9. `([^ \n]+) \(` -> `\1( `
10. `([^ \n]+)\)` -> `\1 )`
11. `\(\)` -> `()`
12. `\( \)` -> `()`
13. `([^ \n]+) \{` -> `\1} `
14. `([^ \n]+)\}` -> `\1 }`
15. `\{\}` -> `{}`
16. `\{ \}` -> `{}`

Notes:

- Rules are intentionally executed as written, including duplicates.
- Some mappings may look unusual (for example bracket/brace variants); this is intentional and mirrors configured behavior.

## Reverse Rules for `deallmanize`

`deallmanize` applies the inverse list in reverse order, as final step.

1. `\{\}` -> `{ }`
2. `\{\}` -> `{}`
3. `([^ \n]+) \}` -> `\1}`
4. `([^ \n]+)\}` -> `\1 {`
5. `\(\)` -> `( )`
6. `\(\)` -> `()`
7. `([^ \n]+) \)` -> `\1)`
8. `([^ \n]+)\(` -> `\1 (`
9. `\[\]` -> `[ ]`
10. `\[\]` -> `[]`
11. `([^ \n]+) \]` -> `\1[`
12. `([^ \n]+)\]` -> `\1 [`
13. `\(\)` -> `( )`
14. `\(\)` -> `()`
15. `([^ \n]+) \)` -> `\1)`
16. `([^ \n]+)\(` -> `\1 (`

## Idempotence (Convergence)

Both commands are designed to be idempotent:

- Running `allmanize` twice yields the same result as running it once.
- Running `deallmanize` twice yields the same result as running it once.

Why this now converges:

- Indentation depth is computed from structural braces only:
  - leading `}` on a line decreases indentation for that line
  - trailing `{` on a line increases indentation for following lines
- Braces appearing in non-structural positions are not used for indentation depth.
- Strings/comments are excluded from all brace and replacement logic.

## Implementation Notes

## Indentation style

Indentation unit follows view settings:

- `translate_tabs_to_spaces`
- `tab_size`

## Newline preservation

The command preserves line-ending style:

- `\n` or `\r\n`

Trailing newline is preserved.

## Scope and limitations

- Designed for practical formatting workflows, not full language parsing.
- String support is specifically single and double quotes.
- Comment support includes `//`, `#`, and `/* ... */` (multiline aware).
- PHP declaration detection in `deallmanize` is heuristic regex-based context scanning.

## Development

## Local validation

You can validate syntax from shell:

```bash
PYTHONPYCACHEPREFIX=/tmp python3 -m py_compile allmanize.py deallmanize.py
```

## Suggested smoke test

1. Start from a file in one of the supported language scopes with mixed brace/spacing styles.
2. Run `allmanize` once and run it again; verify no second change.
3. Run `deallmanize` once and run it again; verify no second change.
4. Confirm strings/comments remain unchanged.

## License

No license file is currently included in this repository.

## Personal Profile and Resume

Hi, I'm **Samantha Allman**

I live in **Reggio Emilia**, Italy

Profile summary:

- Born in San Francisco on September 12, 2001.
- Age: 24 (as of March 1, 2026).
- Moved to Italy in 2019 at age 18.
- Studied software engineering in Bologna.
- Graduated in 2024 at age 23.
- Moved to Reggio Emilia and started working at Kalei after graduation.

Currently I'm programmer at Kalei, I respond directly to Paolo Bertani.
