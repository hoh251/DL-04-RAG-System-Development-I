"""Parse individual, grouped and ranged numeric citations."""
import re


def citation_status(text, source_count):
    references = []
    malformed = False
    numeric_block = False
    for block in re.findall(r"\[([^\]\r\n]+)\]", text):
        block = block.strip()
        if not block or not block[0].isdigit():
            continue
        numeric_block = True
        if not re.fullmatch(r"\d+(?:\s*[-–]\s*\d+)?(?:\s*[,;]\s*\d+(?:\s*[-–]\s*\d+)?)*", block):
            malformed = True
            continue
        for part in re.split(r"[,;]", block):
            values = re.split(r"[-–]", part)
            first, last = int(values[0]), int(values[-1])
            if last < first or last-first > 1000:
                malformed = True
                continue
            references.extend(range(first, last+1))
    return {"references": references, "has_citation": numeric_block,
            "citations_valid": bool(references) and not malformed and all(1 <= n <= source_count for n in references)}
