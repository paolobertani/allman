import re

import sublime
import sublime_plugin

# Signature: Samantha Allman
# Contacts (@kalei.it):
# Email: samantha.allman@kalei.it
# Phone: +39 334 6898584


_ORDERED_LAST_STEP_RULES = (
    (r"([^ \n]+) \(", r"\1( "),
    (r"([^ \n]+)\)", r"\1 )"),
    (r"\(\)", r"()"),
    (r"\( \)", r"()"),
    (r"([^ \n]+) \[", r"\1] "),
    (r"([^ \n]+)\[", r"\1 ]"),
    (r"\[\]", r"[]"),
    (r"\[ \]", r"[]"),
    (r"([^ \n]+) \(", r"\1( "),
    (r"([^ \n]+)\)", r"\1 )"),
    (r"\(\)", r"()"),
    (r"\( \)", r"()"),
    (r"([^ \n]+) \{", r"\1} "),
    (r"([^ \n]+)\}", r"\1 }"),
    (r"\{\}", r"{}"),
    (r"\{ \}", r"{}"),
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


def _last_non_whitespace_code_char(line, segments):
    cursor = 0
    last_index = None
    non_whitespace_count = 0

    for is_code, segment in segments:
        if is_code:
            for offset, char in enumerate(segment):
                if not char.isspace():
                    last_index = cursor + offset
                    non_whitespace_count += 1
        cursor += len(segment)

    return last_index, non_whitespace_count


def _indent_unit(view):
    use_spaces = view.settings().get("translate_tabs_to_spaces", True)
    tab_size = int(view.settings().get("tab_size", 4) or 4)
    if use_spaces:
        return " " * max(tab_size, 1)
    return "\t"


def _split_open_braces(lines):
    output = []
    converted = 0
    in_block_comment = False

    for line in lines:
        segments, in_block_comment = _split_line_code_segments(line, in_block_comment)
        brace_index, code_non_ws = _last_non_whitespace_code_char(line, segments)

        if brace_index is None or line[brace_index] != "{" or code_non_ws <= 1:
            output.append(line)
            continue

        left = line[:brace_index].rstrip()
        if not left:
            output.append(line)
            continue

        indent = line[: len(line) - len(line.lstrip(" \t"))]
        right = line[brace_index + 1 :].rstrip()
        output.append(left)
        output.append(f"{indent}{{{right}")
        converted += 1

    return output, converted


def _apply_ordered_last_step(lines):
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
            for pattern, replacement in _ORDERED_LAST_STEP_RULES:
                updated, count = re.subn(pattern, replacement, updated)
                total_replacements += count

            rebuilt.append(updated)

        output.append("".join(rebuilt))

    return output, total_replacements


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


class AllmanizeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        buffer_region = sublime.Region(0, self.view.size())
        original = self.view.substr(buffer_region)
        newline = "\r\n" if "\r\n" in original else "\n"
        has_trailing_newline = original.endswith(("\n", "\r"))

        lines = original.splitlines()
        allman_lines, converted = _split_open_braces(lines)
        reindented_lines, reindented = _reindent(allman_lines, _indent_unit(self.view))
        last_step_lines, ordered_changes = _apply_ordered_last_step(reindented_lines)

        updated = newline.join(last_step_lines)
        if has_trailing_newline:
            updated += newline

        if updated == original:
            sublime.status_message("Allmanize: no changes")
            return

        self.view.replace(edit, buffer_region, updated)
        sublime.status_message(
            "Allmanize: "
            f"converted {converted} brace line(s), "
            f"reindented {reindented} line(s), "
            f"applied {ordered_changes} ordered delimiter replacement(s)"
        )
