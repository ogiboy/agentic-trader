import { App, Octokit } from "octokit";
import { getGithubAppConfig, owner, repo } from "@/lib/feedback/github-config";

let instance: Octokit | undefined;

export async function getOctokit(): Promise<Octokit> {
  if (instance) return instance;

  const { appId, privateKey } = getGithubAppConfig();

  if (!appId || !privateKey) {
    throw new Error(
      "GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY are required in docs/.env.local for GitHub docs feedback forwarding.",
    );
  }

  const app = new App({
    appId,
    privateKey,
  });

  const { data } = await app.octokit.request(
    "GET /repos/{owner}/{repo}/installation",
    {
      owner,
      repo,
      headers: {
        "X-GitHub-Api-Version": "2022-11-28",
      },
    },
  );

  instance = await app.getInstallationOctokit(data.id);
  return instance;
}
