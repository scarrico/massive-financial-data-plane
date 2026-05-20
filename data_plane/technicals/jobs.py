from __future__ import annotations


def artifact_chunks(artifacts: list[dict], size: int) -> list[list[dict]]:
    if size < 1:
        raise ValueError("artifacts_per_card must be at least 1")
    return [artifacts[index : index + size] for index in range(0, len(artifacts), size)]
