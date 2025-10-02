'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import Slide, { SlideProps } from '@mui/material/Slide';

// 슬라이드 애니메이션 컴포넌트
function SlideTransition(props: SlideProps) {
  return <Slide {...props} direction="up" />;
}

// 공지 타입 정의
interface Announcement {
  id: number;
  message: string;
  is_active: boolean;
  created_at: string;
}

export default function AnnouncementHandler() {
  const [announcement, setAnnouncement] = useState<Announcement | null>(null);
  const [open, setOpen] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [isClient, setIsClient] = useState(false);
  const [showConnectionStatus, setShowConnectionStatus] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  // SSE 연결 함수
  const connectToSSE = useCallback(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    console.log('🔌 공지 시스템 연결 중...', apiUrl);
    setConnectionStatus('connecting');

    const eventSource = new EventSource(`${apiUrl}/api/v1/community/announcements/stream`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('✅ 공지 시스템 연결 성공');
      setConnectionStatus('connected');
      reconnectAttemptsRef.current = 0; // 연결 성공 시 재시도 횟수 리셋
    };

    eventSource.onmessage = (event) => {
      try {
        const data: Announcement[] = JSON.parse(event.data);
        console.log('📢 새 공지 수신:', data);

        // Find the first active announcement
        const activeAnnouncement = data.find(announcement => announcement.is_active);

        if (activeAnnouncement) {
          setAnnouncement(activeAnnouncement);
          setOpen(true);
        } else {
          console.log('🔇 모든 공지 비활성화됨');
          setOpen(false);
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
      
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
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

  useEffect(() => {
    // Ensure dev-only UI that may be mutated by extensions only renders on client
    setIsClient(true);

    // 로컬 스토리지에서 연결 상태 표시 설정 읽기 (기본값: true)
    const storedShowConnectionStatus = localStorage.getItem('showConnectionStatus');
    setShowConnectionStatus(storedShowConnectionStatus !== 'false');

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

  const handleClose = useCallback((event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpen(false);
  }, []);

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

  const handleToggleConnectionStatus = useCallback(() => {
    const newShowStatus = !showConnectionStatus;
    setShowConnectionStatus(newShowStatus);
    localStorage.setItem('showConnectionStatus', newShowStatus.toString());
  }, [showConnectionStatus]);

  return (
    <>
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

      {process.env.NODE_ENV === 'development' && isClient && showConnectionStatus && (
        <div suppressHydrationWarning style={{
          position: 'fixed',
          top: 10,
          right: 10,
          display: 'flex',
          flexDirection: 'row',
          gap: '8px',
          zIndex: 9999
        }}>
          {/* 연결 상태 아이콘 */}
          <div style={{
            padding: '4px 8px',
            backgroundColor: connectionStatus === 'connected' ? '#4caf50' :
                           connectionStatus === 'connecting' ? '#ff9800' : '#f44336',
            color: 'white',
            borderRadius: '4px',
            fontSize: '12px',
            cursor: connectionStatus === 'disconnected' ? 'pointer' : 'default'
          }} onClick={connectionStatus === 'disconnected' ? handleReconnect : undefined}>
            {connectionStatus === 'connected' && '🟢'}
            {connectionStatus === 'connecting' && '🟡 연결 중...'}
            {connectionStatus === 'disconnected' && '🔴 연결 끊김 (클릭하여 재연결)'}
          </div>

          {/* 토글 버튼 */}
          <div style={{
            padding: '4px 8px',
            backgroundColor: '#2196f3',
            color: 'white',
            borderRadius: '4px',
            fontSize: '12px',
            cursor: 'pointer',
            userSelect: 'none'
          }} onClick={handleToggleConnectionStatus}>
            {showConnectionStatus ? '🔵 켜짐' : '⚪ 꺼짐'}
          </div>
        </div>
      )}
    </>
  );
}
