import type { ActionResponse } from "@/components/feedback/schema";
import { getFeedbackDestination } from "@/lib/feedback/github-destination";
import { docsCategory, owner, repo } from "@/lib/feedback/github-config";
import { getOctokit } from "@/lib/feedback/github-client";

export async function createDiscussionThread(
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
      forwarding: "succeeded",
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
    forwarding: "succeeded",
    storedAt: "runtime/docs-feedback.jsonl",
    githubUrl: result.createDiscussion.discussion.url,
  };
}
