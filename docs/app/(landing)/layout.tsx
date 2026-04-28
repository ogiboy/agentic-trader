import type { ReactNode } from 'react';

export default function LandingRootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return children;
}
