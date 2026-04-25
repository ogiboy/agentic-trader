import { createMDX } from 'fumadocs-mdx/next';
import { dirname } from 'node:path';

const githubPagesBasePath =
  process.env.GITHUB_PAGES === 'true'
    ? `/${process.env.GITHUB_PAGES_REPO_NAME ?? 'agentic-trader'}`
    : '';
const repoRoot = dirname(import.meta.dirname);

/** @type {import("next").NextConfig} */
const config = {
  output: 'export',
  reactStrictMode: true,
  trailingSlash: true,
  ...(githubPagesBasePath ? { basePath: githubPagesBasePath } : {}),
  env: {
    NEXT_PUBLIC_BASE_PATH: githubPagesBasePath,
  },
  turbopack: {
    root: repoRoot,
  },
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
      {
        protocol: 'https',
        hostname: 'ui.shadcn.com',
      },
    ],
  },
};

const withMDX = createMDX();

export default withMDX(config);
