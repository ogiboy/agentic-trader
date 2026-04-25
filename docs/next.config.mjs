import { createMDX } from 'fumadocs-mdx/next';

/** @type {import("next").NextConfig} */
const config = {
  reactStrictMode: true,
  turbopack: {
    root: import.meta.dirname,
  },
  images: {
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
