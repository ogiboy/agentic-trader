export const CHAT_PERSONAS = [
  'operator_liaison',
  'regime_analyst',
  'strategy_selector',
  'risk_steward',
  'portfolio_manager',
] as const;

export type ChatPersona = (typeof CHAT_PERSONAS)[number];

export const CHAT_PERSONA_LABELS: Record<ChatPersona, string> = {
  operator_liaison: 'Operator Assistant',
  regime_analyst: 'Market Regime Analyst',
  strategy_selector: 'Strategy Selector',
  risk_steward: 'Risk Steward',
  portfolio_manager: 'Portfolio Manager',
};

export function formatChatPersona(value: unknown): string {
  return isChatPersona(value) ? CHAT_PERSONA_LABELS[value] : String(value || '-');
}

export function isChatPersona(value: unknown): value is ChatPersona {
  return (
    typeof value === 'string' && CHAT_PERSONAS.includes(value as ChatPersona)
  );
}
