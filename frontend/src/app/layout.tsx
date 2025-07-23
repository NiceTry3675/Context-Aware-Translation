'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import Slide, { SlideProps } from '@mui/material/Slide';
import { Analytics } from '@vercel/analytics/react';
import theme from '../theme';
import "./globals.css";

// 슬라이드 애니메이션 컴포넌트
function SlideTransition(props: SlideProps) {
  return <Slide {...props} direction="up" />;
}

// Metadata는 더 이상 export할 수 없습니다. 'use client'에서는 지원되지 않습니다.
// 이 정보가 필요하다면, 각 page.tsx에서 개별적으로 설정해야 합니다.
// export const metadata: Metadata = {
//   title: "냥번역 - Context-Aware AI Novel Translator",
//   description: "소설 번역을 위한 AI 번역 서비스",
// };

// 공지 타입 정의
interface Announcement {
  id: number;
  message: string;
  is_active: boolean;
  created_at: string;
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [announcement, setAnnouncement] = useState<Announcement | null>(null);
  const [open, setOpen] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  // SSE 연결 함수
  const connectToSSE = useCallback(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    console.log('🔌 공지 시스템 연결 중...', apiUrl);
    setConnectionStatus('connecting');

    const eventSource = new EventSource(`${apiUrl}/api/v1/announcements/stream`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('✅ 공지 시스템 연결 성공');
      setConnectionStatus('connected');
      reconnectAttemptsRef.current = 0; // 연결 성공 시 재시도 횟수 리셋
    };

    eventSource.onmessage = (event) => {
      try {
        const data: Announcement = JSON.parse(event.data);
        console.log('📢 새 공지 수신:', data);
        
        if (data.is_active) {
          // 활성 공지 - 표시
          setAnnouncement(data);
          setOpen(true);
        } else {
          // 비활성 공지 - 숨기기
          console.log('🔇 공지 비활성화됨:', data.id);
          setOpen(false);
          // 약간의 지연 후 공지 데이터도 제거
          setTimeout(() => {
            setAnnouncement(null);
          }, 300);
        }
      } catch (error) {
        console.error('❌ 공지 데이터 파싱 오류:', error);
      }
    };

    eventSource.onerror = (err) => {
      console.error('❌ SSE 연결 오류:', err);
      setConnectionStatus('disconnected');
      eventSource.close();
      
      // 자동 재연결 로직
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000); // 최대 30초
        console.log(`🔄 ${delay}ms 후 재연결 시도... (${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
        
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttemptsRef.current++;
          connectToSSE();
        }, delay);
      } else {
        console.error('❌ 최대 재연결 시도 횟수 초과');
      }
    };

    return eventSource;
  }, []);

  // 컴포넌트 마운트 시 SSE 연결
  useEffect(() => {
    connectToSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connectToSSE]);

  // 공지 닫기 핸들러
  const handleClose = useCallback((event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpen(false);
  }, []);

  // 수동 재연결 함수
  const handleReconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    reconnectAttemptsRef.current = 0;
    connectToSSE();
  }, [connectToSSE]);

  return (
    <html lang="ko">
      <body>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
          
          {/* 실시간 공지 시스템 */}
          {announcement && announcement.is_active && (
            <Snackbar 
              open={open} 
              autoHideDuration={null} 
              onClose={handleClose} 
              anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
              TransitionComponent={SlideTransition}
              sx={{
                '& .MuiSnackbarContent-root': {
                  backgroundColor: 'transparent',
                  boxShadow: 'none',
                  padding: 0,
                },
              }}
            >
              <Alert 
                onClose={handleClose} 
                severity="info" 
                variant="filled"
                sx={{ 
                  width: '100%',
                  maxWidth: '600px',
                  fontSize: '0.95rem',
                  fontWeight: 500,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                  '& .MuiAlert-message': {
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                  }
                }}
              >
                <span>📢</span>
                {announcement.message}
              </Alert>
            </Snackbar>
          )}

          {/* 연결 상태 표시 (개발 모드에서만) */}
          {process.env.NODE_ENV === 'development' && (
            <div style={{
              position: 'fixed',
              top: 10,
              right: 10,
              padding: '4px 8px',
              backgroundColor: connectionStatus === 'connected' ? '#4caf50' : 
                             connectionStatus === 'connecting' ? '#ff9800' : '#f44336',
              color: 'white',
              borderRadius: '4px',
              fontSize: '12px',
              zIndex: 9999,
              cursor: connectionStatus === 'disconnected' ? 'pointer' : 'default'
            }} onClick={connectionStatus === 'disconnected' ? handleReconnect : undefined}>
              {connectionStatus === 'connected' && '🟢'}
              {connectionStatus === 'connecting' && '🟡 연결 중...'}
              {connectionStatus === 'disconnected' && '🔴 연결 끊김 (클릭하여 재연결)'}
            </div>
          )}
        </ThemeProvider>
        <Analytics />
      </body>
    </html>
  );
}