export const owner = process.env.DOCS_FEEDBACK_GITHUB_OWNER ?? "ogiboy";
export const repo = process.env.DOCS_FEEDBACK_GITHUB_REPO ?? "agentic-trader";
export const docsCategory =
  process.env.DOCS_FEEDBACK_GITHUB_CATEGORY ?? "Docs Feedback";

export function getGithubAppConfig() {
  return {
    appId: process.env.GITHUB_APP_ID,
    privateKey: process.env.GITHUB_APP_PRIVATE_KEY?.replace(/\\n/g, "\n"),
  };
}

export function isGithubFeedbackConfigured() {
  const { appId, privateKey } = getGithubAppConfig();
  return Boolean(appId && privateKey);
}
