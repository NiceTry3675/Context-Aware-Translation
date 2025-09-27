'use client';

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  LinearProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Divider,
  Stack,
  Tooltip,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import StorageIcon from '@mui/icons-material/Storage';
import ClearAllIcon from '@mui/icons-material/ClearAll';
import RefreshIcon from '@mui/icons-material/Refresh';
import InfoIcon from '@mui/icons-material/Info';
import { illustrationStorage } from '../utils/illustrationStorage';

interface StorageStats {
  totalSize: number;
  itemCount: number;
  oldestTimestamp: number;
  newestTimestamp: number;
}

interface JobStorage {
  jobId: string;
  count: number;
  size: number;
}

interface IllustrationStorageManagerProps {
  open: boolean;
  onClose: () => void;
  currentJobId?: string;
}

export default function IllustrationStorageManager({
  open,
  onClose,
  currentJobId,
}: IllustrationStorageManagerProps) {
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [jobStorages, setJobStorages] = useState<JobStorage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const [deleteJobId, setDeleteJobId] = useState<string | null>(null);

  // Format bytes to human-readable size
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  // Format timestamp to date string
  const formatDate = (timestamp: number): string => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleDateString();
  };

  // Load storage statistics
  const loadStats = async () => {
    setLoading(true);
    setError(null);

    try {
      // Check if IndexedDB is supported
      if (!illustrationStorage.isSupported()) {
        setError('Your browser does not support local storage for illustrations');
        return;
      }

      // Get overall stats
      const storageStats = await illustrationStorage.getStorageStats();
      setStats(storageStats);

      // Group by job
      const jobMap = new Map<string, JobStorage>();

      // Get all illustrations (simplified for this example)
      // In a real implementation, you'd want to iterate through all stored items
      // and group them by jobId
      if (currentJobId) {
        const jobIllustrations = await illustrationStorage.getJobIllustrations(currentJobId);
        if (jobIllustrations.length > 0) {
          const jobSize = jobIllustrations.reduce((sum, ill) => sum + ill.size, 0);
          jobMap.set(currentJobId, {
            jobId: currentJobId,
            count: jobIllustrations.length,
            size: jobSize,
          });
        }
      }

      setJobStorages(Array.from(jobMap.values()));
    } catch (err) {
      console.error('Failed to load storage stats:', err);
      setError('Failed to load storage information');
    } finally {
      setLoading(false);
    }
  };

  // Load stats when dialog opens
  useEffect(() => {
    if (open) {
      loadStats();
    }
  }, [open, currentJobId]);

  // Handle clearing all illustrations
  const handleClearAll = async () => {
    setLoading(true);
    setError(null);

    try {
      await illustrationStorage.clearAll();
      await loadStats(); // Reload stats
      setConfirmClearAll(false);
    } catch (err) {
      console.error('Failed to clear storage:', err);
      setError('Failed to clear storage');
    } finally {
      setLoading(false);
    }
  };

  // Handle deleting job illustrations
  const handleDeleteJob = async (jobId: string) => {
    setLoading(true);
    setError(null);

    try {
      await illustrationStorage.deleteJobIllustrations(jobId);
      await loadStats(); // Reload stats
      setDeleteJobId(null);
    } catch (err) {
      console.error(`Failed to delete job ${jobId}:`, err);
      setError(`Failed to delete illustrations for job ${jobId}`);
    } finally {
      setLoading(false);
    }
  };

  // Calculate storage usage percentage (assuming 500MB max)
  const maxStorage = 500 * 1024 * 1024; // 500MB
  const usagePercentage = stats ? (stats.totalSize / maxStorage) * 100 : 0;

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <StorageIcon />
            <Typography variant="h6">Illustration Storage Manager</Typography>
          </Box>
        </DialogTitle>

        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {!illustrationStorage.isSupported() ? (
            <Alert severity="warning">
              Your browser does not support local storage for illustrations.
              Illustrations will be fetched from the server each time.
            </Alert>
          ) : (
            <>
              {/* Storage Usage */}
              <Box mb={3}>
                <Typography variant="subtitle1" gutterBottom>
                  Storage Usage
                </Typography>
                <Box display="flex" alignItems="center" gap={2}>
                  <Box flexGrow={1}>
                    <LinearProgress
                      variant="determinate"
                      value={usagePercentage}
                      sx={{ height: 10, borderRadius: 5 }}
                      color={usagePercentage > 80 ? 'error' : usagePercentage > 60 ? 'warning' : 'primary'}
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 100 }}>
                    {stats ? formatBytes(stats.totalSize) : '0 Bytes'} / 500 MB
                  </Typography>
                </Box>
              </Box>

              {/* Statistics */}
              {stats && (
                <Box mb={3}>
                  <Typography variant="subtitle1" gutterBottom>
                    Statistics
                  </Typography>
                  <Stack spacing={1}>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        Total Items:
                      </Typography>
                      <Typography variant="body2">{stats.itemCount}</Typography>
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        Oldest Item:
                      </Typography>
                      <Typography variant="body2">{formatDate(stats.oldestTimestamp)}</Typography>
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        Newest Item:
                      </Typography>
                      <Typography variant="body2">{formatDate(stats.newestTimestamp)}</Typography>
                    </Box>
                  </Stack>
                </Box>
              )}

              <Divider sx={{ my: 2 }} />

              {/* Job-specific storage */}
              <Box mb={2}>
                <Typography variant="subtitle1" gutterBottom>
                  Stored Jobs
                </Typography>
                {jobStorages.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No illustrations stored locally
                  </Typography>
                ) : (
                  <List>
                    {jobStorages.map((job) => (
                      <ListItem key={job.jobId}>
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="body1">
                                Job {job.jobId}
                                {job.jobId === currentJobId && (
                                  <Chip label="Current" size="small" color="primary" sx={{ ml: 1 }} />
                                )}
                              </Typography>
                            </Box>
                          }
                          secondary={`${job.count} items • ${formatBytes(job.size)}`}
                        />
                        <ListItemSecondaryAction>
                          <Tooltip title="Delete job illustrations">
                            <IconButton
                              edge="end"
                              onClick={() => setDeleteJobId(job.jobId)}
                              disabled={loading}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                )}
              </Box>

              {/* Info about storage */}
              <Alert severity="info" icon={<InfoIcon />}>
                Illustrations are stored locally in your browser for faster access.
                They will be automatically removed after 30 days or when storage is full.
              </Alert>
            </>
          )}
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() => loadStats()}
            disabled={loading}
            startIcon={<RefreshIcon />}
          >
            Refresh
          </Button>
          <Box flexGrow={1} />
          <Button
            onClick={() => setConfirmClearAll(true)}
            disabled={loading || !stats || stats.itemCount === 0}
            color="error"
            startIcon={<ClearAllIcon />}
          >
            Clear All
          </Button>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Confirmation dialog for clearing all */}
      <Dialog open={confirmClearAll} onClose={() => setConfirmClearAll(false)}>
        <DialogTitle>Confirm Clear All</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to clear all locally stored illustrations?
            This action cannot be undone, but you can re-download illustrations
            from the server when needed.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmClearAll(false)}>Cancel</Button>
          <Button onClick={handleClearAll} color="error" variant="contained">
            Clear All
          </Button>
        </DialogActions>
      </Dialog>

      {/* Confirmation dialog for deleting job */}
      <Dialog open={!!deleteJobId} onClose={() => setDeleteJobId(null)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete all illustrations for job {deleteJobId}?
            You can re-download them from the server when needed.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteJobId(null)}>Cancel</Button>
          <Button
            onClick={() => deleteJobId && handleDeleteJob(deleteJobId)}
            color="error"
            variant="contained"
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}