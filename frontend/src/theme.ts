"use client";
import { createTheme } from '@mui/material/styles';
import { Inter } from 'next/font/google';

const inter = Inter({
  weight: ["300", "400", "500", "700"],
  subsets: ["latin"],
  display: "swap",
});

// Create a theme instance with mobile-first responsive breakpoints
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#81d4fa', // Light Blue
    },
    secondary: {
      main: '#f48fb1', // Light Pink
    },
    success: {
      main: '#a5d6a7', // Light Green
    },
    warning: {
      main: '#ffe082', // Light Yellow
    },
    info: {
      main: '#b39ddb', // Light Purple
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
    text: {
      primary: '#ffffff',
      secondary: 'rgba(255, 255, 255, 0.7)',
    },
  },
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 900,
      lg: 1200,
      xl: 1536,
    },
  },
  typography: {
    fontFamily: inter.style.fontFamily,
    h1: {
      fontSize: 'clamp(2rem, 5vw, 3.5rem)',
      fontWeight: 700,
    },
    h2: {
      fontSize: 'clamp(1.5rem, 4vw, 2.5rem)',
      fontWeight: 700,
    },
    h3: {
      fontSize: 'clamp(1.25rem, 3vw, 1.75rem)',
      fontWeight: 700,
    },
    h4: {
      fontSize: 'clamp(1.1rem, 2.5vw, 1.5rem)',
      fontWeight: 600,
    },
    h5: {
      fontSize: 'clamp(1rem, 2vw, 1.25rem)',
      fontWeight: 600,
    },
    h6: {
      fontSize: 'clamp(0.9rem, 1.5vw, 1.1rem)',
      fontWeight: 600,
    },
    body1: {
      fontSize: 'clamp(0.875rem, 1.5vw, 1rem)',
    },
    body2: {
      fontSize: 'clamp(0.8rem, 1.2vw, 0.875rem)',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 'bold',
        },
      },
    },
    MuiCard: {
        styleOverrides: {
            root: {
                borderRadius: 16,
                border: '1px solid rgba(255, 255, 255, 0.12)',
            }
        }
    },
    MuiTextField: {
        styleOverrides: {
            root: {
                '& .MuiOutlinedInput-root': {
                    borderRadius: 8,
                },
            },
        },
    },
    MuiToggleButton: {
        styleOverrides: {
            root: {
                '&.Mui-selected': {
                    backgroundColor: 'rgba(129, 212, 250, 0.16)', // primary.main with alpha
                    color: '#81d4fa', // primary.main
                    '&:hover': {
                        backgroundColor: 'rgba(129, 212, 250, 0.24)',
                    }
                }
            }
        }
    }
  }
});

export default theme;
