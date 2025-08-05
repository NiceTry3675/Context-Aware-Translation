import {
  Paper, Typography, TableContainer, Table, TableHead, TableRow,
  TableCell, TableBody, Alert, Link
} from '@mui/material';
import { AutoStories as AutoStoriesIcon, MenuBook as MenuBookIcon } from '@mui/icons-material';
import JobRow from './JobRow';
import { Job } from '../../types/job';

interface JobsTableProps {
  jobs: Job[];
  onDelete: (jobId: number) => void;
  onDownload: (url: string, filename: string) => void;
  onOpenSidebar: (job: Job) => void;
  onTriggerValidation: (jobId: number) => void;
  onTriggerPostEdit: (jobId: number) => void;
  onDownloadValidationReport: (jobId: number) => void;
  onDownloadPostEditLog: (jobId: number) => void;
  devMode?: boolean;
  apiUrl: string;
}

export default function JobsTable({
  jobs,
  onDelete,
  onDownload,
  onOpenSidebar,
  onTriggerValidation,
  onTriggerPostEdit,
  onDownloadValidationReport,
  onDownloadPostEditLog,
  devMode = false,
  apiUrl
}: JobsTableProps) {
  const hasProcessingJobs = jobs.some(job => job.status === 'PROCESSING');
  const hasCompletedJobs = jobs.some(job => job.status === 'COMPLETED' && !job.filename.toLowerCase().endsWith('.epub'));

  return (
    <>
      <Typography variant="h2" component="h2" textAlign="center" gutterBottom>
        Translation Jobs
      </Typography>
      
      {hasProcessingJobs && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <strong>안내:</strong> 번역 작업은 내부적으로 여러 단계를 거칩니다. 첫 챕터(약 5~10분)의 분석 및 번역이 완료될 때까지 진행률이 0%로 표시될 수 있으니 잠시만 기다려주세요.
        </Alert>
      )}

      {hasCompletedJobs && (
        <Alert severity="success" icon={<MenuBookIcon fontSize="inherit" />} sx={{ mb: 2 }}>
          <strong>팁:</strong> 완료된 TXT 파일은{' '}
          <Link href="https://calibre-ebook.com/download" target="_blank" rel="noopener noreferrer" sx={{ fontWeight: 'bold' }}>
            Calibre
          </Link>
          {' '}
          를 사용하여 EPUB 등 원하는 전자책 형식으로 쉽게 변환할 수 있습니다.
        </Alert>
      )}

      {jobs.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>파일명</TableCell>
                <TableCell>상태</TableCell>
                <TableCell>소요 시간</TableCell>
                <TableCell align="right">작업</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs.map((job) => (
                <JobRow
                  key={`job-row-${job.id}`}
                  job={job}
                  onDelete={onDelete}
                  onDownload={onDownload}
                  onOpenSidebar={onOpenSidebar}
                  onTriggerValidation={onTriggerValidation}
                  onTriggerPostEdit={onTriggerPostEdit}
                  onDownloadValidationReport={onDownloadValidationReport}
                  onDownloadPostEditLog={onDownloadPostEditLog}
                  devMode={devMode}
                  apiUrl={apiUrl}
                />
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Paper sx={{ p: 4, textAlign: 'center', backgroundColor: 'rgba(255, 255, 255, 0.05)' }}>
          <AutoStoriesIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" component="p">
            아직 번역한 작업이 없네요.
          </Typography>
          <Typography color="text.secondary">
            첫 번째 소설을 번역해보세요!
          </Typography>
        </Paper>
      )}
    </>
  );
}