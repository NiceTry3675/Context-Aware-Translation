'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Container,
  Divider,
  Grid,
  Stack,
  Typography,
} from '@mui/material';
import NoSsr from '@mui/material/NoSsr';
import RefreshIcon from '@mui/icons-material/Refresh';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

import { getCachedClerkToken } from '../utils/authToken';
import { fetchWithRetry } from '../utils/fetchWithRetry';
import type { components } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type TokenUsageDashboard = components['schemas']['TokenUsageDashboard'];
type ModelTokenUsage = components['schemas']['ModelTokenUsage'];

type LoadOptions = {
  silent?: boolean;
};

const numberFormatter = new Intl.NumberFormat();

function UsageMetricCard({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <Card
      elevation={highlight ? 4 : 1}
      sx={{
        borderRadius: 2,
        height: '100%',
        border: theme => (highlight ? `1px solid ${theme.palette.primary.main}` : undefined),
      }}
    >
      <CardContent>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          {label}
        </Typography>
        <Typography variant="h5" fontWeight={highlight ? 700 : 600} color={highlight ? 'primary.main' : 'text.primary'}>
          {numberFormatter.format(value)}
        </Typography>
      </CardContent>
    </Card>
  );
}

function ModelUsageCard({ usage }: { usage: ModelTokenUsage }) {
  return (
    <Card sx={{ borderRadius: 2, height: '100%' }}>
      <CardContent>
        <Stack spacing={1.5}>
          <Typography variant="subtitle1" fontWeight={600}>
            {usage.model}
          </Typography>
          <Divider />
          <Stack spacing={1}>
            <Stack direction="row" justifyContent="space-between">
              <Typography variant="body2" color="text.secondary">
                입력 토큰
              </Typography>
              <Typography variant="body2" fontWeight={600}>
                {numberFormatter.format(usage.input_tokens)}
              </Typography>
            </Stack>
            <Stack direction="row" justifyContent="space-between">
              <Typography variant="body2" color="text.secondary">
                출력 토큰
              </Typography>
              <Typography variant="body2" fontWeight={600}>
                {numberFormatter.format(usage.output_tokens)}
              </Typography>
            </Stack>
            <Divider flexItem sx={{ my: 1 }} />
            <Stack direction="row" justifyContent="space-between">
              <Typography variant="body2" color="text.secondary">
                총 사용량
              </Typography>
              <Typography variant="body2" fontWeight={700} color="primary.main">
                {numberFormatter.format(usage.total_tokens)}
              </Typography>
            </Stack>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function TokenUsagePage() {
  const router = useRouter();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [data, setData] = useState<TokenUsageDashboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);

  const hasUsage = useMemo(() => {
    if (!data) return false;
    const totals = data.total;
    return (
      (totals?.total_tokens ?? 0) > 0 ||
      (totals?.input_tokens ?? 0) > 0 ||
      (totals?.output_tokens ?? 0) > 0 ||
      (data.per_model?.length ?? 0) > 0
    );
  }, [data]);

  const fetchUsage = useCallback(
    async ({ silent = false }: LoadOptions = {}) => {
      if (!isSignedIn) {
        return;
      }

      if (!silent) {
        setLoading(true);
      }
      setError(null);

      try {
        const token = await getCachedClerkToken(getToken);
        if (!token) {
          throw new Error('인증 토큰을 가져오지 못했습니다. 다시 로그인해 주세요.');
        }

        const response = await fetchWithRetry(
          `${API_BASE_URL}/api/v1/users/me/token-usage`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          },
          { retries: 2, timeoutMs: 8000 }
        );

        if (!response.ok) {
          throw new Error('토큰 사용량 정보를 불러오지 못했습니다.');
        }

        const payload: TokenUsageDashboard = await response.json();
        setData(payload);
        setLastRefreshedAt(new Date());
      } catch (err) {
        const message = err instanceof Error ? err.message : '토큰 사용량을 불러오는 중 오류가 발생했습니다.';
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [getToken, isSignedIn]
  );

  useEffect(() => {
    if (!isLoaded) {
      return;
    }

    if (!isSignedIn) {
      router.replace('/about');
      return;
    }

    void fetchUsage();
  }, [isLoaded, isSignedIn, router, fetchUsage]);

  const lastUpdatedLabel = useMemo(() => {
    const source = data?.last_updated ? new Date(data.last_updated) : null;
    if (!source) {
      return lastRefreshedAt ? lastRefreshedAt.toLocaleString() : null;
    }
    return source.toLocaleString();
  }, [data?.last_updated, lastRefreshedAt]);

  return (
    <NoSsr>
      <Container maxWidth="md" sx={{ py: { xs: 4, md: 6 } }}>
      <Stack spacing={4}>
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} alignItems={{ xs: 'stretch', md: 'center' }}>
          <Box>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              토큰 사용량
            </Typography>
            <Typography variant="body2" color="text.secondary">
              모델별 입력/출력 토큰 사용량을 확인하세요.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button
              variant="outlined"
              color="inherit"
              startIcon={<ArrowBackIcon />}
              onClick={() => router.push('/')}
            >
              작업 공간으로 이동
            </Button>
            <Button
              variant="contained"
              startIcon={<RefreshIcon />}
              onClick={() => fetchUsage({ silent: false })}
              disabled={loading}
            >
              새로고침
            </Button>
          </Stack>
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}

        {loading && !data ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 240 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Stack spacing={4}>
            <Card sx={{ borderRadius: 2 }}>
              <CardContent>
                <Stack spacing={2}>
                  <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} spacing={1}>
                    <Typography variant="h6" fontWeight={600}>
                      총 사용량 요약
                    </Typography>
                    {lastUpdatedLabel && (
                      <Typography variant="body2" color="text.secondary">
                        최근 업데이트: {lastUpdatedLabel}
                      </Typography>
                    )}
                  </Stack>
                  {data ? (
                    <Box display="grid" gridTemplateColumns={{ xs: '1fr', sm: 'repeat(3, 1fr)' }} gap={2}>
                      <UsageMetricCard label="입력 토큰" value={data.total.input_tokens} />
                      <UsageMetricCard label="출력 토큰" value={data.total.output_tokens} />
                      <UsageMetricCard label="총 토큰" value={data.total.total_tokens} highlight />
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      아직 사용량 데이터가 없습니다.
                    </Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>

            <Card sx={{ borderRadius: 2 }}>
              <CardContent>
                <Stack spacing={2}>
                  <Typography variant="h6" fontWeight={600}>
                    모델별 사용량
                  </Typography>
                  {data && data.per_model.length > 0 ? (
                    <Box display="grid" gridTemplateColumns={{ xs: '1fr', sm: 'repeat(2, 1fr)' }} gap={2}>
                      {data.per_model.map(modelUsage => (
                        <ModelUsageCard key={modelUsage.model} usage={modelUsage} />
                      ))}
                    </Box>
                  ) : (
                    <Alert severity="info" sx={{ borderRadius: 2 }}>
                      {hasUsage
                        ? '모델별 사용량 데이터를 계산할 수 없습니다. 잠시 후 다시 시도해 주세요.'
                        : '아직 토큰 사용 기록이 없습니다. 번역을 시작하면 여기에서 사용량을 확인할 수 있어요.'}
                    </Alert>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        )}
      </Stack>
      </Container>
    </NoSsr>
  );
}
