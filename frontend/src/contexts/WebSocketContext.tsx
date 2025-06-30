import React, { createContext, useContext, useEffect, useRef, useState, ReactNode } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { io, Socket } from 'socket.io-client';
import { RootState } from '../store/store';
import { updateUserPresence, addCollaborator, removeCollaborator } from '../store/slices/collaborationSlice';
import { addComment, updateComment } from '../store/slices/documentsSlice';
import { addNotification } from '../store/slices/notificationsSlice';

interface WebSocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  connectToDocument: (documentId: string) => void;
  disconnectFromDocument: () => void;
  sendMessage: (message: any) => void;
  updatePresence: (presence: any) => void;
  sendDocumentChange: (change: any) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentDocumentId, setCurrentDocumentId] = useState<string | null>(null);
  
  const { user, token } = useSelector((state: RootState) => state.auth);
  const dispatch = useDispatch();
  
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const heartbeatIntervalRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (user && token) {
      initializeConnection();
    } else {
      cleanupConnection();
    }

    return () => {
      cleanupConnection();
    };
  }, [user, token]);

  const initializeConnection = () => {
    const wsEndpoint = process.env.REACT_APP_WEBSOCKET_ENDPOINT || 'ws://localhost:3001';
    
    const newSocket = io(wsEndpoint, {
      auth: {
        token,
        userId: user?.id,
      },
      transports: ['websocket'],
      upgrade: true,
      rememberUpgrade: true,
      timeout: 20000,
      forceNew: true,
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      clearTimeout(reconnectTimeoutRef.current);
      
      // Start heartbeat
      heartbeatIntervalRef.current = setInterval(() => {
        newSocket.emit('ping');
      }, 30000);
    });

    newSocket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      setIsConnected(false);
      clearInterval(heartbeatIntervalRef.current);
      
      // Attempt reconnection if not intentional
      if (reason !== 'io client disconnect') {
        attemptReconnection();
      }
    });

    newSocket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      setIsConnected(false);
      attemptReconnection();
    });

    // Document collaboration events
    newSocket.on('user_joined', (data) => {
      console.log('User joined:', data);
      dispatch(addCollaborator({
        documentId: data.documentId,
        user: data.user,
      }));
      
      dispatch(addNotification({
        type: 'info',
        title: 'User Joined',
        message: `${data.user.firstName} ${data.user.lastName} joined the document`,
        documentId: data.documentId,
      }));
    });

    newSocket.on('user_left', (data) => {
      console.log('User left:', data);
      dispatch(removeCollaborator({
        documentId: data.documentId,
        userId: data.userId,
      }));
    });

    newSocket.on('presence_update', (data) => {
      dispatch(updateUserPresence({
        documentId: data.documentId,
        userId: data.userId,
        presence: data.presence,
      }));
    });

    newSocket.on('document_change', (data) => {
      console.log('Document change received:', data);
      // Handle operational transformation here
      handleDocumentChange(data);
    });

    newSocket.on('new_comment', (data) => {
      console.log('New comment received:', data);
      dispatch(addComment({
        documentId: data.documentId,
        comment: data.comment,
      }));
      
      dispatch(addNotification({
        type: 'info',
        title: 'New Comment',
        message: `${data.comment.userName} added a comment`,
        documentId: data.documentId,
      }));
    });

    newSocket.on('comment_resolved', (data) => {
      dispatch(updateComment({
        documentId: data.documentId,
        commentId: data.commentId,
        updates: { status: 'resolved' },
      }));
    });

    newSocket.on('workflow_update', (data) => {
      console.log('Workflow update received:', data);
      dispatch(addNotification({
        type: data.status === 'approved' ? 'success' : data.status === 'rejected' ? 'error' : 'info',
        title: 'Workflow Update',
        message: `Document workflow ${data.status}`,
        documentId: data.documentId,
      }));
    });

    newSocket.on('notification', (data) => {
      console.log('Real-time notification:', data);
      dispatch(addNotification(data));
    });

    newSocket.on('error', (error) => {
      console.error('WebSocket error:', error);
      dispatch(addNotification({
        type: 'error',
        title: 'Connection Error',
        message: 'Lost connection to collaboration server',
      }));
    });

    setSocket(newSocket);
  };

  const cleanupConnection = () => {
    if (socket) {
      socket.disconnect();
      setSocket(null);
    }
    setIsConnected(false);
    setCurrentDocumentId(null);
    clearTimeout(reconnectTimeoutRef.current);
    clearInterval(heartbeatIntervalRef.current);
  };

  const attemptReconnection = () => {
    clearTimeout(reconnectTimeoutRef.current);
    reconnectTimeoutRef.current = setTimeout(() => {
      console.log('Attempting to reconnect...');
      if (user && token) {
        initializeConnection();
      }
    }, 5000);
  };

  const connectToDocument = (documentId: string) => {
    if (!socket || !isConnected) {
      console.warn('Socket not connected, cannot join document');
      return;
    }

    // Leave current document if any
    if (currentDocumentId && currentDocumentId !== documentId) {
      socket.emit('leave_document', { documentId: currentDocumentId });
    }

    // Join new document
    socket.emit('join_document', { 
      documentId,
      userId: user?.id,
      userName: `${user?.firstName} ${user?.lastName}`,
    });
    
    setCurrentDocumentId(documentId);
    console.log('Joined document:', documentId);
  };

  const disconnectFromDocument = () => {
    if (socket && currentDocumentId) {
      socket.emit('leave_document', { documentId: currentDocumentId });
      setCurrentDocumentId(null);
      console.log('Left document:', currentDocumentId);
    }
  };

  const sendMessage = (message: any) => {
    if (socket && isConnected) {
      socket.emit('message', message);
    }
  };

  const updatePresence = (presence: any) => {
    if (socket && isConnected && currentDocumentId) {
      socket.emit('presence_update', {
        documentId: currentDocumentId,
        userId: user?.id,
        presence: {
          ...presence,
          timestamp: new Date().toISOString(),
        },
      });
    }
  };

  const sendDocumentChange = (change: any) => {
    if (socket && isConnected && currentDocumentId) {
      socket.emit('document_change', {
        documentId: currentDocumentId,
        userId: user?.id,
        change: {
          ...change,
          timestamp: new Date().toISOString(),
          version: Date.now(), // Simple versioning
        },
      });
    }
  };

  const handleDocumentChange = (data: any) => {
    // Implement operational transformation here
    // This is a simplified version - in production, use a proper OT library
    try {
      const { change, userId } = data;
      
      // Don't apply changes from current user (already applied locally)
      if (userId === user?.id) {
        return;
      }

      // Apply the change to the document
      // This would integrate with your document editor (Monaco, Draft.js, etc.)
      console.log('Applying remote change:', change);
      
      // Dispatch to store if needed
      // dispatch(applyDocumentChange(change));
      
    } catch (error) {
      console.error('Error applying document change:', error);
    }
  };

  const contextValue: WebSocketContextType = {
    socket,
    isConnected,
    connectToDocument,
    disconnectFromDocument,
    sendMessage,
    updatePresence,
    sendDocumentChange,
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};