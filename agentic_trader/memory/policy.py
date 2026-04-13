from typing import Literal, TypeAlias, TypedDict


MemoryDomain: TypeAlias = Literal["trade_memory", "chat_memory"]
MemoryActor: TypeAlias = Literal[
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
    allowed = MEMORY_WRITE_POLICIES[domain]["allowed_actors"]
    if actor not in allowed:
        raise PermissionError(
            f"Memory write blocked: actor '{actor}' cannot write to '{domain}'."
        )


def memory_write_policy_snapshot() -> dict[str, MemoryWritePolicy]:
    return {
        domain: {
            "allowed_actors": list(policy["allowed_actors"]),
            "note": policy["note"],
        }
        for domain, policy in MEMORY_WRITE_POLICIES.items()
    }
