
from dataclasses import dataclass, field


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str


class ConversationMemory:
    """
    Sliding-window conversation memory.

    Keeps the last `max_exchanges` user-assistant pairs.
    When the window is full, oldest exchanges are dropped.

    Think of it like a fixed-size queue â€” new messages push out old ones.
    """

    def __init__(self, max_exchanges: int = 10):
        """
        Args:
            max_exchanges: How many back-and-forth exchanges to remember.
                          10 exchanges = 20 messages (10 user + 10 assistant).
                          More exchanges = more context but more tokens/cost.
        """
        self.max_exchanges = max_exchanges
        self.messages: list[Message] = []

    def add_user_message(self, content: str):
        """Record what the user said."""
        self.messages.append(Message(role="user", content=content))

    def add_assistant_message(self, content: str):
        """Record what the agent responded."""
        self.messages.append(Message(role="assistant", content=content))
        self._trim()

    def _trim(self):
        """
        Keep only the last N exchanges.
        An exchange = 1 user message + 1 assistant message = 2 messages.
        So we keep the last (max_exchanges * 2) messages.
        """
        max_messages = self.max_exchanges * 2
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]

    def get_history_string(self) -> str:
        """
        Format history as a simple string for injection into prompts.

        Returns something like:
            User: What is order ORD-001?
            Assistant: Order ORD-001 is for 500 SSD-4TB units...
            User: Should we expedite it?
        """
        if not self.messages:
            return "No previous conversation."

        lines = []
        for msg in self.messages:
            role_label = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{role_label}: {msg.content}")
        return "\n".join(lines)

    def clear(self):
        """Reset memory â€” start fresh."""
        self.messages = []

    def __len__(self) -> int:
        return len(self.messages)

