import type { Metadata, Viewport } from "next";
import "./globals.css";
import { ClerkProvider } from '@clerk/nextjs';
import { koKR } from '@clerk/localizations';
import { Analytics } from '@vercel/analytics/react';
import { Noto_Sans_KR } from 'next/font/google';

const notoSansKr = Noto_Sans_KR({
  subsets: ['latin'],
  display: 'swap',
  weight: ['400', '600', '700'],
});


export const metadata: Metadata = {
  title: "냥번역 - 서비스 종료 안내",
  description: "냥번역 서비스 운영 종료 안내",
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className={notoSansKr.className}>
        <ClerkProvider localization={koKR}>
          {children}
          <Analytics />
        </ClerkProvider>
      </body>
    </html>
  );
}
