import { Container, Typography, Box, Link, Paper } from '@mui/material';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '개인정보처리방침 - 냥번역',
  description: '냥번역(CATRANS) 서비스의 개인정보처리방침입니다.',
};

export default function SimplePrivacyPolicyPage() {
  return (
    <Container maxWidth="md" sx={{ py: { xs: 4, md: 8 } }}>
      <Paper sx={{ p: { xs: 3, md: 5 } }}>
        <Typography variant="h3" component="h1" align="center" gutterBottom>
          개인정보처리방침
        </Typography>
        <Typography align="center" color="text.secondary" sx={{ mb: 5 }}>
          냥번역 서비스는 사용자의 개인정보를 소중히 다룹니다.
        </Typography>

        <Box sx={{ my: 3 }}>
          <Typography variant="h5" gutterBottom>1. 수집 정보 및 이용 목적</Typography>
          <Typography paragraph>
            서비스는 Google 계정으로 로그인 시, 회원 식별 및 서비스 제공을 위해 아래 정보만을 수집하고 사용합니다.
          </Typography>
          <Typography component="ul" sx={{ pl: 2, listStyleType: 'disc' }}>
            <li><strong>수집 정보:</strong> 이름, 이메일 주소</li>
            <li><strong>이용 목적:</strong> 사용자 식별 및 로그인 상태 유지</li>
          </Typography>
        </Box>

        <Box sx={{ my: 3 }}>
          <Typography variant="h5" gutterBottom>2. 개인정보 처리 위탁</Typography>
          <Typography paragraph>
            서비스는 안정적이고 안전한 기능 제공을 위해, 신뢰할 수 있는 아래 외부 전문 업체의 도움을 받습니다.
          </Typography>
          <Typography component="ul" sx={{ pl: 2, listStyleType: 'disc' }}>
            <li>
              <strong>Clerk:</strong> 회원가입 및 로그인 기능 처리.{' '}
              <Link href="https://clerk.com/privacy" target="_blank" rel="noopener noreferrer">[정책 보기]</Link>
            </li>
            <li>
              <strong>Railway:</strong> 서버 인프라 운영 및 데이터베이스 관리.{' '}
              <Link href="https://railway.app/legal/privacy" target="_blank" rel="noopener noreferrer">[정책 보기]</Link>
            </li>
          </Typography>
        </Box>

        <Box sx={{ my: 3 }}>
          <Typography variant="h5" gutterBottom>3. 정보 보관 및 권리</Typography>
          <Typography paragraph>
            수집된 정보는 회원 탈퇴 시까지 보관되며, 사용자는 언제든지 서비스 내에서 계정 삭제를 통해 정보를 영구적으로 파기할 수 있습니다.
          </Typography>
        </Box>

        <Box sx={{ my: 3 }}>
          <Typography variant="h5" gutterBottom>4. 문의</Typography>
          <Typography paragraph>
            개인정보 관련 문의는 아래 이메일로 연락주시기 바랍니다.
          </Typography>
          <Typography sx={{ pl: 2 }}>
            <strong>이메일:</strong> tomtom5330@gmail.com
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
}