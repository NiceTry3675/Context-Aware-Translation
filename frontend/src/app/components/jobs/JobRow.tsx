import { TableRow, TableCell, Typography } from '@mui/material';
import { Job } from '../../types/job';
import JobStatusIndicator from './components/JobStatusIndicator';
import DownloadActions from './components/DownloadActions';

interface JobRowProps {
  job: Job;
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

const formatDuration = (start: string, end: string | null): string => {
  if (!end) return '';
  const startDate = new Date(start);
  const endDate = new Date(end);
  const seconds = Math.floor((endDate.getTime() - startDate.getTime()) / 1000);
  if (seconds < 60) return `${seconds}초`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}분 ${remainingSeconds}초`;
};

export default function JobRow({
  job,
  onDelete,
  onDownload,
  onOpenSidebar,
  onTriggerValidation,
  onTriggerPostEdit,
  onDownloadValidationReport,
  onDownloadPostEditLog,
  devMode = false,
  apiUrl
}: JobRowProps) {
  const handleDownloadTranslation = () => {
    const extension = job.filename.toLowerCase().endsWith('.epub') ? 'epub' : 'txt';
    const filename = `${job.filename.split('.')[0]}_translated.${extension}`;
    onDownload(`${apiUrl}/api/v1/jobs/${job.id}/output`, filename);
  };

  const handleDownloadGlossary = () => {
    const filename = `${job.filename.split('.')[0]}_glossary.json`;
    onDownload(`${apiUrl}/api/v1/jobs/${job.id}/glossary`, filename);
  };

  const handleDownloadPromptLogs = () => {
    const filename = `prompts_job_${job.id}_${job.filename.split('.')[0]}.txt`;
    onDownload(`${apiUrl}/api/v1/jobs/${job.id}/logs/prompts`, filename);
  };

  const handleDownloadContextLogs = () => {
    const filename = `context_job_${job.id}_${job.filename.split('.')[0]}.txt`;
    onDownload(`${apiUrl}/api/v1/jobs/${job.id}/logs/context`, filename);
  };

  return (
    <TableRow hover>
      <TableCell component="th" scope="row">
        <Typography variant="body2" noWrap title={job.filename} sx={{ maxWidth: '300px' }}>
          {job.filename}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {new Date(job.created_at).toLocaleString()}
        </Typography>
      </TableCell>
      <TableCell>
        <JobStatusIndicator
          status={job.status}
          errorMessage={job.error_message}
          progress={job.progress}
          validationEnabled={job.validation_enabled}
          validationStatus={job.validation_status || undefined}
          validationProgress={job.validation_progress}
          postEditEnabled={job.post_edit_enabled}
          postEditStatus={job.post_edit_status || undefined}
          postEditProgress={job.post_edit_progress}
        />
      </TableCell>
      <TableCell>
        {job.status === 'COMPLETED' ? formatDuration(job.created_at, job.completed_at) : '-'}
      </TableCell>
      <TableCell align="right">
        <DownloadActions
          job={job}
          onDownloadTranslation={handleDownloadTranslation}
          onDownloadGlossary={handleDownloadGlossary}
          onDownloadPromptLogs={handleDownloadPromptLogs}
          onDownloadContextLogs={handleDownloadContextLogs}
          onDownloadValidationReport={() => onDownloadValidationReport(job.id)}
          onDownloadPostEditLog={() => onDownloadPostEditLog(job.id)}
          onOpenSidebar={() => onOpenSidebar(job)}
          onTriggerValidation={() => onTriggerValidation(job.id)}
          onTriggerPostEdit={() => onTriggerPostEdit(job.id)}
          onDelete={() => onDelete(job.id)}
          devMode={devMode}
        />
      </TableCell>
    </TableRow>
  );
}