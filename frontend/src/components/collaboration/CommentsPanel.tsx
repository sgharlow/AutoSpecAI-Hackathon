import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  IconButton,
  TextField,
  Button,
  Avatar,
  Chip,
  Menu,
  MenuItem,
  Divider,
  Paper,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Badge,
} from '@mui/material';
import {
  Close as CloseIcon,
  Add as AddIcon,
  Reply as ReplyIcon,
  MoreVert as MoreVertIcon,
  Check as ResolveIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../../store/store';
import {
  fetchDocumentComments,
  createComment,
  resolveComment,
} from '../../store/slices/documentsSlice';
import { Comment } from '../../store/slices/documentsSlice';
import { formatDistanceToNow } from 'date-fns';

interface CommentsPanelProps {
  documentId: string;
  canComment: boolean;
  onClose: () => void;
}

interface CommentItemProps {
  comment: Comment;
  replies: Comment[];
  onReply: (threadId: string, content: string) => void;
  onResolve: (commentId: string) => void;
  onEdit: (commentId: string, content: string) => void;
  onDelete: (commentId: string) => void;
  canComment: boolean;
}

const CommentItem: React.FC<CommentItemProps> = ({
  comment,
  replies,
  onReply,
  onResolve,
  onEdit,
  onDelete,
  canComment,
}) => {
  const [showReplyField, setShowReplyField] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(comment.content);
  
  const { user } = useSelector((state: RootState) => state.auth);
  const isOwner = user?.id === comment.userId;
  const isResolved = comment.status === 'resolved';

  const handleReply = () => {
    if (replyContent.trim()) {
      onReply(comment.threadId, replyContent);
      setReplyContent('');
      setShowReplyField(false);
    }
  };

  const handleEdit = () => {
    if (editContent.trim() && editContent !== comment.content) {
      onEdit(comment.commentId, editContent);
      setIsEditing(false);
    } else {
      setIsEditing(false);
      setEditContent(comment.content);
    }
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        mb: 1,
        border: 1,
        borderColor: isResolved ? 'success.light' : 'divider',
        bgcolor: isResolved ? 'success.50' : 'background.paper',
        opacity: isResolved ? 0.7 : 1,
      }}
    >
      {/* Comment Header */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Avatar sx={{ width: 32, height: 32 }}>
            {comment.userId.charAt(0).toUpperCase()}
          </Avatar>
          <Box>
            <Typography variant="subtitle2" fontWeight={600}>
              {comment.userId}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatDistanceToNow(new Date(comment.timestamp), { addSuffix: true })}
            </Typography>
          </Box>
          {isResolved && (
            <Chip
              label="Resolved"
              size="small"
              color="success"
              variant="outlined"
            />
          )}
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          {!isResolved && canComment && (
            <Tooltip title="Resolve">
              <IconButton
                size="small"
                onClick={() => onResolve(comment.commentId)}
                color="success"
              >
                <ResolveIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
          
          <IconButton
            size="small"
            onClick={handleMenuOpen}
          >
            <MoreVertIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      {/* Comment Content */}
      <Box sx={{ mb: 1 }}>
        {isEditing ? (
          <Box>
            <TextField
              fullWidth
              multiline
              rows={3}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              variant="outlined"
              size="small"
              sx={{ mb: 1 }}
            />
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button size="small" onClick={handleEdit} variant="contained">
                Save
              </Button>
              <Button size="small" onClick={() => setIsEditing(false)}>
                Cancel
              </Button>
            </Box>
          </Box>
        ) : (
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {comment.content}
          </Typography>
        )}
      </Box>

      {/* Annotation Info */}
      {comment.annotationData && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
            "{comment.annotationData.selectedText}"
          </Typography>
        </Box>
      )}

      {/* Comment Actions */}
      {!isResolved && canComment && (
        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
          <Button
            size="small"
            startIcon={<ReplyIcon />}
            onClick={() => setShowReplyField(!showReplyField)}
          >
            Reply
          </Button>
        </Box>
      )}

      {/* Reply Field */}
      {showReplyField && (
        <Box sx={{ mt: 2, pl: 4 }}>
          <TextField
            fullWidth
            multiline
            rows={2}
            placeholder="Write a reply..."
            value={replyContent}
            onChange={(e) => setReplyContent(e.target.value)}
            variant="outlined"
            size="small"
            sx={{ mb: 1 }}
          />
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              size="small"
              onClick={handleReply}
              variant="contained"
              disabled={!replyContent.trim()}
            >
              Reply
            </Button>
            <Button size="small" onClick={() => setShowReplyField(false)}>
              Cancel
            </Button>
          </Box>
        </Box>
      )}

      {/* Replies */}
      {replies.length > 0 && (
        <Box sx={{ mt: 2, pl: 4, borderLeft: 2, borderColor: 'divider' }}>
          {replies.map((reply) => (
            <CommentItem
              key={reply.commentId}
              comment={reply}
              replies={[]}
              onReply={onReply}
              onResolve={onResolve}
              onEdit={onEdit}
              onDelete={onDelete}
              canComment={canComment}
            />
          ))}
        </Box>
      )}

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        {isOwner && (
          <MenuItem
            onClick={() => {
              setIsEditing(true);
              handleMenuClose();
            }}
          >
            <EditIcon sx={{ mr: 1 }} fontSize="small" />
            Edit
          </MenuItem>
        )}
        {isOwner && (
          <MenuItem
            onClick={() => {
              onDelete(comment.commentId);
              handleMenuClose();
            }}
          >
            <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
            Delete
          </MenuItem>
        )}
      </Menu>
    </Paper>
  );
};

export const CommentsPanel: React.FC<CommentsPanelProps> = ({
  documentId,
  canComment,
  onClose,
}) => {
  const dispatch = useDispatch();
  const { documentComments } = useSelector((state: RootState) => state.documents);
  const [newComment, setNewComment] = useState('');
  const [filter, setFilter] = useState<'all' | 'unresolved' | 'resolved'>('all');
  const [selectedText, setSelectedText] = useState('');
  const newCommentRef = useRef<HTMLTextAreaElement>(null);

  const comments = documentComments[documentId] || [];

  useEffect(() => {
    dispatch(fetchDocumentComments(documentId));
  }, [dispatch, documentId]);

  // Group comments by thread
  const commentThreads = comments.reduce((threads, comment) => {
    if (comment.type === 'comment') {
      threads[comment.threadId] = {
        comment,
        replies: comments.filter(c => c.threadId === comment.threadId && c.type === 'reply'),
      };
    }
    return threads;
  }, {} as Record<string, { comment: Comment; replies: Comment[] }>);

  // Filter threads
  const filteredThreads = Object.values(commentThreads).filter(thread => {
    switch (filter) {
      case 'unresolved':
        return thread.comment.status !== 'resolved';
      case 'resolved':
        return thread.comment.status === 'resolved';
      default:
        return true;
    }
  });

  const unresolvedCount = Object.values(commentThreads).filter(
    thread => thread.comment.status !== 'resolved'
  ).length;

  const handleCreateComment = async () => {
    if (!newComment.trim()) return;

    const commentData = {
      documentId,
      content: newComment,
      ...(selectedText && {
        annotationData: {
          selectedText,
          selectionStart: 0, // These would come from the editor
          selectionEnd: selectedText.length,
          position: { line: 1, column: 1 },
        },
      }),
    };

    await dispatch(createComment(commentData));
    setNewComment('');
    setSelectedText('');
  };

  const handleReply = async (threadId: string, content: string) => {
    const replyData = {
      documentId,
      content,
      threadId,
    };

    await dispatch(createComment(replyData));
  };

  const handleResolve = async (commentId: string) => {
    await dispatch(resolveComment({ documentId, commentId }));
  };

  const handleEdit = async (commentId: string, content: string) => {
    // TODO: Implement edit comment
    console.log('Edit comment:', commentId, content);
  };

  const handleDelete = async (commentId: string) => {
    // TODO: Implement delete comment
    console.log('Delete comment:', commentId);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">
            Comments
            {unresolvedCount > 0 && (
              <Badge badgeContent={unresolvedCount} color="primary" sx={{ ml: 1 }} />
            )}
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Filter Buttons */}
        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
          <Button
            size="small"
            variant={filter === 'all' ? 'contained' : 'outlined'}
            onClick={() => setFilter('all')}
          >
            All ({Object.keys(commentThreads).length})
          </Button>
          <Button
            size="small"
            variant={filter === 'unresolved' ? 'contained' : 'outlined'}
            onClick={() => setFilter('unresolved')}
          >
            Open ({unresolvedCount})
          </Button>
          <Button
            size="small"
            variant={filter === 'resolved' ? 'contained' : 'outlined'}
            onClick={() => setFilter('resolved')}
          >
            Resolved ({Object.keys(commentThreads).length - unresolvedCount})
          </Button>
        </Box>
      </Box>

      {/* New Comment */}
      {canComment && (
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          {selectedText && (
            <Box sx={{ mb: 1, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Commenting on:
              </Typography>
              <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                "{selectedText}"
              </Typography>
            </Box>
          )}
          
          <TextField
            ref={newCommentRef}
            fullWidth
            multiline
            rows={3}
            placeholder="Add a comment..."
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            variant="outlined"
            size="small"
            sx={{ mb: 1 }}
          />
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Button
              startIcon={<AddIcon />}
              onClick={handleCreateComment}
              variant="contained"
              size="small"
              disabled={!newComment.trim()}
            >
              Comment
            </Button>
            
            {selectedText && (
              <Button
                size="small"
                onClick={() => setSelectedText('')}
              >
                Clear Selection
              </Button>
            )}
          </Box>
        </Box>
      )}

      {/* Comments List */}
      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {filteredThreads.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body2" color="text.secondary">
              {filter === 'all' && 'No comments yet'}
              {filter === 'unresolved' && 'No open comments'}
              {filter === 'resolved' && 'No resolved comments'}
            </Typography>
          </Box>
        ) : (
          filteredThreads.map(({ comment, replies }) => (
            <CommentItem
              key={comment.commentId}
              comment={comment}
              replies={replies}
              onReply={handleReply}
              onResolve={handleResolve}
              onEdit={handleEdit}
              onDelete={handleDelete}
              canComment={canComment}
            />
          ))
        )}
      </Box>
    </Box>
  );
};