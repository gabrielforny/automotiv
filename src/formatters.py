from __future__ import annotations

import re


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def format_cpf(value: str) -> str:
    digits = only_digits(value)
    if len(digits) != 11:
        return value
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def format_cnpj(value: str) -> str:
    digits = only_digits(value)
    if len(digits) != 14:
        return value
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def cpf_cnpj_search_variations(value: str) -> list[str]:
    digits = only_digits(value)
    if len(digits) == 11:
        return [format_cpf(digits), digits]
    if len(digits) == 14:
        return [format_cnpj(digits), digits]
    return [value.strip()]


def code_search_variations(code: str) -> list[str]:
    """Gera variações do código para busca no site (troca -, espaço e ponto entre si)."""
    base = code.strip()
    candidates = [base]
    for src, replacements in [("-", [" ", ".", ""]), (" ", ["-", ".", ""]), (".", ["-", " ", ""])]:
        if src in base:
            for rep in replacements:
                candidates.append(base.replace(src, rep))
    return list(dict.fromkeys(candidates))
