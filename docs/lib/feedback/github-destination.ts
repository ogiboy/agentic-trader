import { getOctokit } from "@/lib/feedback/github-client";
import { owner, repo } from "@/lib/feedback/github-config";

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

export async function getFeedbackDestination(): Promise<RepositoryInfo> {
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

  cachedDestination = repository;
  return repository;
}
