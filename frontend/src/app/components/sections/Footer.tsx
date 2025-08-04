import { Box, Typography, Button, Link } from '@mui/material';
import {
  Coffee as CoffeeIcon,
  Email as EmailIcon,
} from '@mui/icons-material';
import theme from '../../../theme';

export default function Footer() {
  return (
    <Box textAlign="center" mt={10} pt={4} borderTop={1} borderColor="divider">
      <Typography variant="h6" gutterBottom>이 서비스가 마음에 드셨나요?</Typography>
      <Typography color="text.secondary" mb={2}>여러분의 소중한 후원은 서비스 유지 및 기능 개선에 큰 힘이 됩니다.</Typography>
      <Box>
        <Button
          variant="contained"
          startIcon={<CoffeeIcon />}
          href="https://coff.ee/nicetry3675"
          target="_blank"
          rel="noopener noreferrer"
          sx={{
            mr: 1,
            backgroundColor: theme.palette.warning.main,
            color: theme.palette.getContrastText(theme.palette.warning.main),
            '&:hover': {
              backgroundColor: '#ffca28'
            }
          }}
        >
          Buy Me a Coffee
        </Button>
        <Button
          variant="outlined"
          startIcon={<EmailIcon />}
          href="https://forms.gle/st93J7NT2PLcxgaj9"
          target="_blank"
          rel="noopener noreferrer"
        >
          Contact Us
        </Button>
      </Box>
      <Box mt={2}>
        <Link href="/privacy" color="text.secondary" variant="body2">
          개인정보처리방침
        </Link>
      </Box>
    </Box>
  );
}