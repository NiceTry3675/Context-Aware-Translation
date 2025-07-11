import type { Metadata } from "next";
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from '../theme'; // 테마 파일을 분리하여 import
import "./globals.css";

export const metadata: Metadata = {
  title: "냥번역 - Context-Aware AI Novel Translator",
  description: "소설 번역을 위한 AI 번역 서비스",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
