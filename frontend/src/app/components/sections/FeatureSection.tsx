import { Box, Typography, Card } from '@mui/material';
import {
  AccountTree as AccountTreeIcon,
  Spellcheck as SpellcheckIcon,
  Style as StyleIcon,
} from '@mui/icons-material';
import theme from '../../../theme';

const featureItems = [
  {
    icon: <AccountTreeIcon sx={{ fontSize: 40 }} />,
    title: "문맥 유지",
    text: "소설 전체의 분위기와 등장인물의 말투를 분석하여, 챕터가 넘어가도 번역 품질이 흔들리지 않습니다.",
    color: theme.palette.primary.main,
  },
  {
    icon: <SpellcheckIcon sx={{ fontSize: 40 }} />,
    title: "용어 일관성",
    text: "고유명사나 특정 용어가 번역될 때마다 달라지는 문제를 해결했습니다. 중요한 단어는 항상 동일하게 번역됩니다.",
    color: theme.palette.success.main,
  },
  {
    icon: <StyleIcon sx={{ fontSize: 40 }} />,
    title: "스타일 유지",
    text: "작가 특유의 문체나 작품의 스타일을 학습하여, 원작의 느낌을 최대한 살린 번역을 제공합니다.",
    color: theme.palette.info.main,
  },
];

export default function FeatureSection() {
  return (
    <Box mb={{ xs: 6, sm: 10 }} px={{ xs: 2, sm: 0 }}>
      <Typography
        variant="h2"
        component="h2"
        textAlign="center"
        gutterBottom
        sx={{ px: { xs: 1, sm: 0 } }}
      >
        냥번역은 무엇이 다른가요?
      </Typography>
      <Typography
        textAlign="center"
        color="text.secondary"
        maxWidth="md"
        mx="auto"
        mb={{ xs: 3, sm: 5 }}
        sx={{ px: { xs: 2, sm: 0 } }}
      >
        단순한 번역기를 넘어, 소설의 맛을 살리는 데 집중했습니다. 일반 생성형 AI 번역에서 발생하는 고질적인 문제들을 해결하여, 처음부터 끝까지 일관성 있는 고품질 번역을 경험할 수 있습니다.
      </Typography>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(auto-fit, minmax(250px, 1fr))' },
          gap: { xs: 2, sm: 4 }
        }}
      >
        {featureItems.map(item => (
          <Card
            key={item.title}
            sx={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              p: { xs: 2, sm: 3 },
              textAlign: 'center'
            }}
          >
            <Box
              mb={2}
              sx={{
                width: { xs: 60, sm: 80 },
                height: { xs: 60, sm: 80 },
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: `${item.color}20`,
                color: item.color,
                boxShadow: `0 0 20px ${item.color}40`,
              }}
            >
              {item.icon}
            </Box>
            <Typography variant="h5" component="h3" gutterBottom>
              {item.title}
            </Typography>
            <Typography color="text.secondary">{item.text}</Typography>
          </Card>
        ))}
      </Box>
    </Box>
  );
}