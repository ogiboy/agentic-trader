function normalizeChatHistory(data) {
  const entries = data?.chatHistory?.entries || [];
  return [...entries].reverse().map((entry) => ({
    user: entry.user_message,
    persona: entry.persona,
    response: entry.response_text,
  }));
}

export { normalizeChatHistory };
