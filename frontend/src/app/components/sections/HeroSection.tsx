import { Box, Typography, Chip } from '@mui/material';

export default function HeroSection() {
  return (
    <Box textAlign="center" mb={10}>
      <Box display="flex" justifyContent="center" alignItems="center" gap={2}>
        <Typography variant="h1" component="h1" sx={{
          background: `linear-gradient(45deg, #00BFFF 30%, #FF69B4 90%)`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          냥번역
        </Typography>
        <Chip label="beta" color="secondary" size="small" />
      </Box>
      <Typography variant="h5" color="text.secondary" component="p" mt={1}>
        <Box component="span" sx={{ color: 'primary.main', fontWeight: 'bold' }}>C</Box>ontext-
        <Box component="span" sx={{ color: 'primary.main', fontWeight: 'bold' }}>A</Box>ware{' '}
        <Box component="span" sx={{ color: 'primary.main', fontWeight: 'bold' }}>T</Box>ranslator
      </Typography>
    </Box>
  );
}