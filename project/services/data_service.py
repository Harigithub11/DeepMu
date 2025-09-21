from typing import List, Tuple

def process_data(data: List[str]) -> List[Tuple[str, int]]:
    return [(item, len(item)) for item in data]