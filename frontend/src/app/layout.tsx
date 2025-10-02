import type { Metadata } from "next";
import "./globals.css";
import { ClerkProvider } from '@clerk/nextjs';
import { koKR } from "@clerk/localizations";
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from '../theme';
import { Analytics } from '@vercel/analytics/react';
import AnnouncementHandler from './components/AnnouncementHandler';
import { Inter } from 'next/font/google';

const inter = Inter({ subsets: ["latin"] });


export const metadata: Metadata = {
  title: "냥번역 - Context-Aware AI Novel Translator",
  description: "소설 번역을 위한 AI 번역 서비스",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <ClerkProvider localization={koKR}>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            <AnnouncementHandler />
            {children}
            <Analytics />
          </ThemeProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
