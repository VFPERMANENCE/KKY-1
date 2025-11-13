import shlex
from typing import Tuple, Optional, List


def parse_command(line: str) -> Tuple[Optional[List[str]], Optional[str]]:
    try:
        tokens = shlex.split(line)
    except ValueError as e:
        return None, f"parse error: {e}"
    return tokens, None