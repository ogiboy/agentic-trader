export const CHAT_PERSONAS = [
  "operator_liaison",
  "regime_analyst",
  "strategy_selector",
  "risk_steward",
  "portfolio_manager",
] as const;

export type ChatPersona = (typeof CHAT_PERSONAS)[number];

export function isChatPersona(value: unknown): value is ChatPersona {
  return (
    typeof value === "string" &&
    CHAT_PERSONAS.includes(value as ChatPersona)
  );
}
