import re

import sublime
import sublime_plugin

# Signature: Samantha Allman
# Contacts (@kalei.it):
# Email: samantha.allman@kalei.it
# Phone: +39 334 6898584


_PHP_IDENTIFIER = r"[A-Za-z_\x80-\xff][\w\x80-\xff]*"
_CLASS_PATTERN = re.compile(
    rf"\b(?:abstract\s+|final\s+|readonly\s+)*class\s+{_PHP_IDENTIFIER}\b",
    re.IGNORECASE,
)
_CLASS_LIKE_PATTERN = re.compile(
    rf"\b(?:interface|trait|enum)\s+{_PHP_IDENTIFIER}\b",
    re.IGNORECASE,
)
_NAMED_FUNCTION_PATTERN = re.compile(
    rf"\bfunction\s+&?\s*{_PHP_IDENTIFIER}\s*\(",
    re.IGNORECASE,
)
_ORDERED_LAST_STEP_REVERSE_RULES = (
    (r"\{\}", r"{ }"),
    (r"\{\}", r"{}"),
    (r"([^ \n]+) \}", r"\1}"),
    (r"([^ \n]+)\}", r"\1 {"),
    (r"\(\)", r"( )"),
    (r"\(\)", r"()"),
    (r"([^ \n]+) \)", r"\1)"),
    (r"([^ \n]+)\(", r"\1 ("),
    (r"\[\]", r"[ ]"),
    (r"\[\]", r"[]"),
    (r"([^ \n]+) \]", r"\1["),
    (r"([^ \n]+)\]", r"\1 ["),
    (r"\(\)", r"( )"),
    (r"\(\)", r"()"),
    (r"([^ \n]+) \)", r"\1)"),
    (r"([^ \n]+)\(", r"\1 ("),
)


def _split_line_code_segments(line, in_block_comment):
    segments = []
    i = 0
    n = len(line)
    code_start = 0

    while i < n:
        if in_block_comment:
            end = line.find("*/", i)
            if end == -1:
                if code_start < i:
                    segments.append((True, line[code_start:i]))
                segments.append((False, line[i:]))
                return segments, True

            if code_start < i:
                segments.append((True, line[code_start:i]))
            segments.append((False, line[i : end + 2]))
            i = end + 2
            code_start = i
            in_block_comment = False
            continue

        char = line[i]
        next_char = line[i + 1] if i + 1 < n else ""

        if char == "/" and next_char == "/":
            if code_start < i:
                segments.append((True, line[code_start:i]))
            segments.append((False, line[i:]))
            return segments, False

        if char == "#":
            if code_start < i:
                segments.append((True, line[code_start:i]))
            segments.append((False, line[i:]))
            return segments, False

        if char == "/" and next_char == "*":
            if code_start < i:
                segments.append((True, line[code_start:i]))

            end = line.find("*/", i + 2)
            if end == -1:
                segments.append((False, line[i:]))
                return segments, True

            segments.append((False, line[i : end + 2]))
            i = end + 2
            code_start = i
            continue

        if char in ("'", '"'):
            if code_start < i:
                segments.append((True, line[code_start:i]))

            quote = char
            start = i
            i += 1
            escaping = False

            while i < n:
                token = line[i]
                if escaping:
                    escaping = False
                elif token == "\\":
                    escaping = True
                elif token == quote:
                    i += 1
                    break
                i += 1

            segments.append((False, line[start:i]))
            code_start = i
            continue

        i += 1

    if code_start < n:
        segments.append((True, line[code_start:n]))

    return segments, False


def _first_non_whitespace_code_char(line, segments):
    cursor = 0
    for is_code, segment in segments:
        if is_code:
            for offset, char in enumerate(segment):
                if not char.isspace():
                    return cursor + offset, char
        cursor += len(segment)
    return None, None


def _indent_unit(view):
    use_spaces = view.settings().get("translate_tabs_to_spaces", True)
    tab_size = int(view.settings().get("tab_size", 4) or 4)
    if use_spaces:
        return " " * max(tab_size, 1)
    return "\t"


def _is_php_view(view):
    if view.size() > 0:
        return view.match_selector(0, "source.php")

    syntax = str(view.settings().get("syntax") or "").lower()
    return "php" in syntax


def _is_comment_line(stripped):
    return (
        stripped.startswith("//")
        or stripped.startswith("#")
        or stripped.startswith("/*")
        or stripped.startswith("*")
        or stripped.startswith("*/")
    )


def _declaration_context(previous_output_lines, limit=24):
    parts = []
    idx = len(previous_output_lines) - 1

    while idx >= 0 and len(parts) < limit:
        stripped = previous_output_lines[idx].strip()
        if stripped == "":
            if parts:
                break
            idx -= 1
            continue

        if _is_comment_line(stripped):
            if parts:
                break
            idx -= 1
            continue

        parts.insert(0, stripped)
        idx -= 1

    return " ".join(parts)


def _is_psr12_definition_context(previous_output_lines):
    context = _declaration_context(previous_output_lines)
    if not context:
        return False

    if _NAMED_FUNCTION_PATTERN.search(context):
        return True

    if _CLASS_PATTERN.search(context):
        return re.search(r"\bnew\s+class\b", context, re.IGNORECASE) is None

    return _CLASS_LIKE_PATTERN.search(context) is not None


def _collapse_open_brace_lines(lines, preserve_psr12_declarations):
    output = []
    converted = 0
    preserved = 0
    in_block_comment = False

    for line in lines:
        segments, in_block_comment = _split_line_code_segments(line, in_block_comment)
        brace_index, brace_char = _first_non_whitespace_code_char(line, segments)

        if brace_char != "{" or brace_index is None:
            output.append(line)
            continue

        if line[:brace_index].strip(" \t") != "":
            output.append(line)
            continue

        if not output:
            output.append(line)
            continue

        if preserve_psr12_declarations and _is_psr12_definition_context(output):
            output.append(line)
            preserved += 1
            continue

        previous = output[-1].rstrip()
        previous_stripped = previous.lstrip(" \t")
        if previous and not (
            _is_comment_line(previous_stripped) or previous_stripped.startswith("#[")
        ):
            tail = line[brace_index + 1 :].rstrip()
            if tail:
                tail = tail if tail[0].isspace() else f" {tail}"
            output[-1] = f"{previous} {{{tail}"
            converted += 1
            continue

        output.append(line)

    return output, converted, preserved


def _brace_stats(line, in_block_comment):
    segments, in_block_comment = _split_line_code_segments(line, in_block_comment)
    code = "".join(segment for is_code, segment in segments if is_code)
    stripped = code.strip()

    if stripped == "":
        return 0, 0, in_block_comment

    leading_closes = 0
    while leading_closes < len(stripped) and stripped[leading_closes] == "}":
        leading_closes += 1

    trailing_opens = 0
    idx = len(stripped) - 1
    while idx >= 0 and stripped[idx] == "{":
        trailing_opens += 1
        idx -= 1

    return trailing_opens - leading_closes, leading_closes, in_block_comment


def _reindent(lines, indent_unit):
    output = []
    depth = 0
    in_block_comment = False
    changed = 0

    for line in lines:
        stripped = line.lstrip(" \t")
        if stripped == "":
            output.append("")
            continue

        net_depth, leading_closes, in_block_comment = _brace_stats(stripped, in_block_comment)
        line_depth = max(depth - leading_closes, 0)
        updated_line = f"{indent_unit * line_depth}{stripped}"

        if updated_line != line:
            changed += 1

        output.append(updated_line)
        depth = max(depth + net_depth, 0)

    return output, changed


def _apply_ordered_reverse_last_step(lines):
    output = []
    total_replacements = 0
    in_block_comment = False

    for line in lines:
        segments, in_block_comment = _split_line_code_segments(line, in_block_comment)
        rebuilt = []

        for is_code, segment in segments:
            if not is_code or segment == "":
                rebuilt.append(segment)
                continue

            updated = segment
            for pattern, replacement in _ORDERED_LAST_STEP_REVERSE_RULES:
                updated, count = re.subn(pattern, replacement, updated)
                total_replacements += count

            rebuilt.append(updated)

        output.append("".join(rebuilt))

    return output, total_replacements


class DeallmanizeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        preserve_psr12_declarations = _is_php_view(self.view)
        buffer_region = sublime.Region(0, self.view.size())
        original = self.view.substr(buffer_region)
        newline = "\r\n" if "\r\n" in original else "\n"
        has_trailing_newline = original.endswith(("\n", "\r"))

        lines = original.splitlines()
        collapsed_lines, converted, preserved = _collapse_open_brace_lines(
            lines, preserve_psr12_declarations
        )
        reindented_lines, reindented = _reindent(collapsed_lines, _indent_unit(self.view))
        last_step_lines, reversed_changes = _apply_ordered_reverse_last_step(reindented_lines)

        updated = newline.join(last_step_lines)
        if has_trailing_newline:
            updated += newline

        if updated == original:
            sublime.status_message("Deallmanize: no changes")
            return

        self.view.replace(edit, buffer_region, updated)
        status = (
            "Deallmanize: "
            f"collapsed {converted} brace line(s), "
            f"reindented {reindented} line(s), "
            f"applied {reversed_changes} reversed ordered replacement(s)"
        )
        if preserve_psr12_declarations:
            status += f", preserved {preserved} PSR-12 declaration brace line(s)"

        sublime.status_message(status)


class DeallmanizePhpCommand(DeallmanizeCommand):
    pass
