import re

# Characters that could be used for prompt injection
CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

# Patterns that look like system/instruction markers
INJECTION_PATTERNS = [
    re.compile(r'\[system[:\s]', re.IGNORECASE),
    re.compile(r'\[instruction[:\s]', re.IGNORECASE),
    re.compile(r'\[admin[:\s]', re.IGNORECASE),
    re.compile(r'<system>', re.IGNORECASE),
    re.compile(r'</system>', re.IGNORECASE),
    re.compile(r'<<\s*SYS\s*>>', re.IGNORECASE),
    re.compile(r'\[INST\]', re.IGNORECASE),
    re.compile(r'\[/INST\]', re.IGNORECASE),
]

# Max lengths
MAX_MESSAGE_LENGTH = 4000
MAX_SENDER_NAME_LENGTH = 50


def sanitize_message(text: str) -> str:
    """Sanitize user message to prevent prompt injection."""
    if not text:
        return ""

    # Remove control characters
    text = CONTROL_CHARS_PATTERN.sub('', text)

    # Neutralize injection patterns by adding zero-width spaces
    for pattern in INJECTION_PATTERNS:
        text = pattern.sub(lambda m: m.group(0)[0] + '\u200b' + m.group(0)[1:], text)

    # Truncate to max length
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[:MAX_MESSAGE_LENGTH] + "..."

    return text


def sanitize_sender_name(name: str) -> str:
    """Sanitize sender name to prevent injection via display name."""
    if not name:
        return "Membre"

    # Remove control characters
    name = CONTROL_CHARS_PATTERN.sub('', name)

    # Remove brackets and other delimiter-like characters
    name = re.sub(r'[\[\]<>{}\n\r]', '', name)

    # Truncate
    if len(name) > MAX_SENDER_NAME_LENGTH:
        name = name[:MAX_SENDER_NAME_LENGTH]

    # If empty after sanitization, use default
    return name.strip() or "Membre"


def wrap_user_content(sender_name: str, message: str) -> str:
    """Wrap user content in XML tags for clear separation."""
    safe_name = sanitize_sender_name(sender_name)
    safe_message = sanitize_message(message)

    return f"""<user_message>
<sender>{safe_name}</sender>
<content>{safe_message}</content>
</user_message>"""


def detect_leaked_system_prompt(response: str) -> bool:
    """Check if response appears to contain leaked system instructions."""
    leak_indicators = [
        "REGLES ABSOLUES",
        "PERSONNALITE",
        "TES OUTILS",
        "PROCESSUS DE REFLEXION",
        "system_instruction",
        "Tu es Regelebot, le pote cinephile",
    ]

    response_upper = response.upper()
    return any(indicator.upper() in response_upper for indicator in leak_indicators)
