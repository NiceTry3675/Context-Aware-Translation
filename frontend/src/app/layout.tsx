'use client';

import { useState, useEffect } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import theme from '../theme';
import "./globals.css";

// Metadata는 더 이상 export할 수 없습니다. 'use client'에서는 지원되지 않습니다.
// 이 정보가 필요하다면, 각 page.tsx에서 개별적으로 설정해야 합니다.
// export const metadata: Metadata = {
//   title: "냥번역 - Context-Aware AI Novel Translator",
//   description: "소설 번역을 위한 AI 번역 서비스",
// };

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [announcement, setAnnouncement] = useState<{ message: string; id: number } | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/announcements/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setAnnouncement(data);
      setOpen(true);
    };

    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const handleClose = (event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpen(false);
  };

  return (
    <html lang="ko">
      <body>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
          {announcement && (
            <Snackbar open={open} autoHideDuration={null} onClose={handleClose} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
              <Alert onClose={handleClose} severity="info" sx={{ width: '100%' }}>
                {announcement.message}
              </Alert>
            </Snackbar>
          )}
        </ThemeProvider>
      </body>
    </html>
  );
}