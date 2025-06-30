import React, { useEffect, useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  IconButton,
  Avatar,
  Chip,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  Alert,
  Fab,
  Tooltip,
} from '@mui/material';
import {
  Description as DocumentIcon,
  Group as CollaborationIcon,
  Workflow as WorkflowIcon,
  Analytics as AnalyticsIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  Assignment as TaskIcon,
  Notifications as NotificationIcon,
  Add as AddIcon,
  Upload as UploadIcon,
  Speed as SpeedIcon,
  CheckCircle as CompletedIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { RootState } from '../../store/store';
import { fetchDocuments } from '../../store/slices/documentsSlice';
import { StatsCard } from '../../components/dashboard/StatsCard';
import { RecentActivity } from '../../components/dashboard/RecentActivity';
import { QuickActions } from '../../components/dashboard/QuickActions';
import { DocumentUploadDialog } from '../../components/documents/DocumentUploadDialog';
import { formatDistanceToNow } from 'date-fns';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  
  const { user } = useSelector((state: RootState) => state.auth);
  const { documents, isLoading } = useSelector((state: RootState) => state.documents);
  const { notifications, unreadCount } = useSelector((state: RootState) => state.notifications);

  useEffect(() => {
    // Fetch recent documents for dashboard
    dispatch(fetchDocuments({ limit: 10 }));
  }, [dispatch]);

  // Calculate statistics
  const stats = {
    totalDocuments: documents.length,
    processingDocuments: documents.filter(doc => doc.status === 'processing').length,
    completedDocuments: documents.filter(doc => doc.status === 'completed').length,
    failedDocuments: documents.filter(doc => doc.status === 'failed').length,
    collaborativeDocuments: documents.filter(doc => doc.metadata.collaborators.length > 1).length,
  };

  // Get recent documents
  const recentDocuments = documents
    .sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime())
    .slice(0, 5);

  // Get pending tasks (mock data - would come from API)
  const pendingTasks = [
    {
      id: '1',
      title: 'Review System Requirements Document',
      type: 'approval',
      dueDate: '2024-01-15T10:00:00Z',
      priority: 'high',
      documentId: 'doc_123',
    },
    {
      id: '2',
      title: 'Approve API Documentation',
      type: 'approval',
      dueDate: '2024-01-16T15:30:00Z',
      priority: 'medium',
      documentId: 'doc_456',
    },
    {
      id: '3',
      title: 'Comment on Design Specifications',
      type: 'review',
      dueDate: '2024-01-17T09:00:00Z',
      priority: 'low',
      documentId: 'doc_789',
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getTaskPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Welcome Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Welcome back, {user?.firstName}!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Here's what's happening with your documents and collaboration.
        </Typography>
      </Box>

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Total Documents"
            value={stats.totalDocuments}
            icon={<DocumentIcon />}
            color="primary"
            trend="+12%"
            subtitle="from last month"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Processing"
            value={stats.processingDocuments}
            icon={<SpeedIcon />}
            color="warning"
            subtitle="in progress"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Completed"
            value={stats.completedDocuments}
            icon={<CompletedIcon />}
            color="success"
            trend="+8%"
            subtitle="this week"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Collaborative"
            value={stats.collaborativeDocuments}
            icon={<CollaborationIcon />}
            color="info"
            subtitle="active sessions"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Recent Documents */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">Recent Documents</Typography>
                <Button
                  size="small"
                  onClick={() => navigate('/documents')}
                >
                  View All
                </Button>
              </Box>
              
              {isLoading ? (
                <LinearProgress />
              ) : recentDocuments.length === 0 ? (
                <Alert severity="info" sx={{ mt: 2 }}>
                  No documents yet. Upload your first document to get started!
                </Alert>
              ) : (
                <List>
                  {recentDocuments.map((document, index) => (
                    <React.Fragment key={document.id}>
                      <ListItem
                        sx={{ px: 0, cursor: 'pointer' }}
                        onClick={() => navigate(`/documents/${document.id}`)}
                      >
                        <ListItemAvatar>
                          <Avatar>
                            <DocumentIcon />
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={document.title}
                          secondary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                              <Chip
                                label={document.status}
                                size="small"
                                color={getStatusColor(document.status) as any}
                                variant="outlined"
                              />
                              <Typography variant="caption" color="text.secondary">
                                {formatDistanceToNow(new Date(document.uploadedAt), { addSuffix: true })}
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < recentDocuments.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Pending Tasks */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">Pending Tasks</Typography>
                <Button
                  size="small"
                  onClick={() => navigate('/workflows')}
                >
                  View All
                </Button>
              </Box>
              
              {pendingTasks.length === 0 ? (
                <Alert severity="success" sx={{ mt: 2 }}>
                  No pending tasks. Great job!
                </Alert>
              ) : (
                <List>
                  {pendingTasks.map((task, index) => (
                    <React.Fragment key={task.id}>
                      <ListItem sx={{ px: 0 }}>
                        <ListItemAvatar>
                          <Avatar>
                            <TaskIcon />
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={task.title}
                          secondary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                              <Chip
                                label={task.priority}
                                size="small"
                                color={getTaskPriorityColor(task.priority) as any}
                                variant="outlined"
                              />
                              <Typography variant="caption" color="text.secondary">
                                Due {formatDistanceToNow(new Date(task.dueDate), { addSuffix: true })}
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < pendingTasks.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Actions */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Quick Actions</Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<UploadIcon />}
                    onClick={() => setUploadDialogOpen(true)}
                    sx={{ py: 2 }}
                  >
                    Upload Document
                  </Button>
                </Grid>
                <Grid item xs={6}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<CollaborationIcon />}
                    onClick={() => navigate('/collaboration')}
                    sx={{ py: 2 }}
                  >
                    Start Collaboration
                  </Button>
                </Grid>
                <Grid item xs={6}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<WorkflowIcon />}
                    onClick={() => navigate('/workflows')}
                    sx={{ py: 2 }}
                  >
                    Create Workflow
                  </Button>
                </Grid>
                <Grid item xs={6}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<AnalyticsIcon />}
                    onClick={() => navigate('/analytics')}
                    sx={{ py: 2 }}
                  >
                    View Analytics
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* System Status & Notifications */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>System Status</Typography>
              
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">Processing Capacity</Typography>
                  <Typography variant="body2">75%</Typography>
                </Box>
                <LinearProgress variant="determinate" value={75} color="success" />
              </Box>

              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">Storage Usage</Typography>
                  <Typography variant="body2">45%</Typography>
                </Box>
                <LinearProgress variant="determinate" value={45} color="primary" />
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'success.main' }} />
                  <Typography variant="caption">All Systems Operational</Typography>
                </Box>
                {unreadCount > 0 && (
                  <Chip
                    label={`${unreadCount} notifications`}
                    size="small"
                    color="primary"
                    icon={<NotificationIcon />}
                  />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Floating Action Button */}
      <Tooltip title="Upload Document" placement="left">
        <Fab
          color="primary"
          sx={{ position: 'fixed', bottom: 16, right: 16 }}
          onClick={() => setUploadDialogOpen(true)}
        >
          <AddIcon />
        </Fab>
      </Tooltip>

      {/* Upload Dialog */}
      <DocumentUploadDialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
      />
    </Box>
  );
};