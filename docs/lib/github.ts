import { App, Octokit } from "octokit";
import {
  blockFeedback,
  pageFeedback,
  type ActionResponse,
  type BlockFeedback,
  type PageFeedback,
} from "@/components/feedback/schema";

export const owner = process.env.DOCS_FEEDBACK_GITHUB_OWNER ?? "ogiboy";
export const repo = process.env.DOCS_FEEDBACK_GITHUB_REPO ?? "agentic-trader";
export const docsCategory =
  process.env.DOCS_FEEDBACK_GITHUB_CATEGORY ?? "Docs Feedback";

let instance: Octokit | undefined;

function getGithubAppConfig() {
  const appId = process.env.GITHUB_APP_ID;
  const privateKey = process.env.GITHUB_APP_PRIVATE_KEY?.replace(/\\n/g, "\n");

  return {
    appId,
    privateKey,
  };
}

export function isGithubFeedbackConfigured() {
  const { appId, privateKey } = getGithubAppConfig();
  return Boolean(appId && privateKey);
}

async function getOctokit(): Promise<Octokit> {
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

interface RepositoryInfo {
  id: string;
  discussionCategories: {
    nodes: {
      id: string;
      name: string;
    }[];
  };
}

let cachedDestination: RepositoryInfo | undefined;

async function getFeedbackDestination() {
  if (cachedDestination) return cachedDestination;

  const octokit = await getOctokit();
  const { repository }: { repository: RepositoryInfo } = await octokit.graphql(`
    query {
      repository(owner: "${owner}", name: "${repo}") {
        id
        discussionCategories(first: 25) {
          nodes { id name }
        }
      }
    }
  `);

  return (cachedDestination = repository);
}

export async function onPageFeedbackAction(
  feedback: PageFeedback,
): Promise<ActionResponse> {
  "use server";

  const parsed = pageFeedback.parse(feedback);

  return createDiscussionThread(
    parsed.url,
    `[${parsed.opinion}] ${parsed.title}\n\n${parsed.message || "No additional note provided."}\n\n> Forwarded from docs page feedback.`,
  );
}

export async function onBlockFeedbackAction(
  feedback: BlockFeedback,
): Promise<ActionResponse> {
  "use server";

  const parsed = blockFeedback.parse(feedback);

  return createDiscussionThread(
    parsed.url,
    `> ${parsed.blockBody ?? parsed.blockId}\n\n[${parsed.opinion}] ${parsed.message || "No additional note provided."}\n\n> Forwarded from docs block feedback.`,
  );
}

async function createDiscussionThread(
  pageId: string,
  body: string,
): Promise<ActionResponse> {
  const octokit = await getOctokit();
  const destination = await getFeedbackDestination();
  const category = destination.discussionCategories.nodes.find(
    (item) => item.name === docsCategory,
  );

  if (!category) {
    throw new Error(
      `Please create a "${docsCategory}" category in GitHub Discussions for ${owner}/${repo}.`,
    );
  }

  const title = `Feedback for ${pageId}`;
  const {
    search: {
      nodes: [discussion],
    },
  }: {
    search: {
      nodes: { id: string; url: string }[];
    };
  } = await octokit.graphql(`
    query {
      search(type: DISCUSSION, query: ${JSON.stringify(`${title} in:title repo:${owner}/${repo} author:@me`)}, first: 1) {
        nodes {
          ... on Discussion { id, url }
        }
      }
    }
  `);

  if (discussion) {
    const result: {
      addDiscussionComment: {
        comment: { id: string; url: string };
      };
    } = await octokit.graphql(`
      mutation {
        addDiscussionComment(input: { body: ${JSON.stringify(body)}, discussionId: "${discussion.id}" }) {
          comment { id, url }
        }
      }
    `);

    return {
      ok: true,
      destination: "github-discussion",
      storedAt: "runtime/docs-feedback.jsonl",
      githubUrl: result.addDiscussionComment.comment.url,
    };
  }

  const result: {
    createDiscussion: { discussion: { id: string; url: string } };
  } = await octokit.graphql(`
    mutation {
      createDiscussion(input: { repositoryId: "${destination.id}", categoryId: "${category.id}", body: ${JSON.stringify(body)}, title: ${JSON.stringify(title)} }) {
        discussion { id, url }
      }
    }
  `);

  return {
    ok: true,
    destination: "github-discussion",
    storedAt: "runtime/docs-feedback.jsonl",
    githubUrl: result.createDiscussion.discussion.url,
  };
}
