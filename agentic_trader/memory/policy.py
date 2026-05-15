from typing import Literal, TypedDict

MemoryDomain = Literal["trade_memory", "chat_memory"]
MemoryActor = Literal[
    "system_runtime",
    "review_agent",
    "operator_chat",
]


class MemoryWritePolicy(TypedDict):
    allowed_actors: list[MemoryActor]
    note: str


MEMORY_WRITE_POLICIES: dict[MemoryDomain, MemoryWritePolicy] = {
    "trade_memory": {
        "allowed_actors": ["system_runtime", "review_agent"],
        "note": "Trading memory is written only from persisted runtime decisions and post-trade review flows.",
    },
    "chat_memory": {
        "allowed_actors": ["operator_chat"],
        "note": "Operator chat history is isolated from trading memory and only chat surfaces may append to it.",
    },
}


def assert_memory_write_allowed(domain: MemoryDomain, actor: MemoryActor) -> None:
    """
    Ensure the specified actor is permitted to write to the given memory domain.

    Parameters:
        domain (MemoryDomain): The memory domain to check (e.g., "trade_memory" or "chat_memory").
        actor (MemoryActor): The actor attempting the write (e.g., "system_runtime", "review_agent", or "operator_chat").

    Raises:
        PermissionError: If the actor is not allowed to write to the domain; message will indicate the blocked actor and domain.
    """
    allowed = MEMORY_WRITE_POLICIES[domain]["allowed_actors"]
    if actor not in allowed:
        raise PermissionError(
            f"Memory write blocked: actor '{actor}' cannot write to '{domain}'."
        )


def memory_write_policy_snapshot() -> dict[str, MemoryWritePolicy]:
    """
    Return a defensive copy of MEMORY_WRITE_POLICIES with mutable lists duplicated.

    Each entry maps a memory domain to a MemoryWritePolicy where `allowed_actors` is a new list copied from the original and `note` is the same string value.

    Returns:
        dict[str, MemoryWritePolicy]: Snapshot of policies; modifying any `allowed_actors` list in the result will not affect the original MEMORY_WRITE_POLICIES.
    """
    return {
        domain: {
            "allowed_actors": list(policy["allowed_actors"]),
            "note": policy["note"],
        }
        for domain, policy in MEMORY_WRITE_POLICIES.items()
    }
