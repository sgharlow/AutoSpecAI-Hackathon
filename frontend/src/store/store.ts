import { configureStore } from '@reduxjs/toolkit';
import { authSlice } from './slices/authSlice';
import { documentsSlice } from './slices/documentsSlice';
import { collaborationSlice } from './slices/collaborationSlice';
import { workflowsSlice } from './slices/workflowsSlice';
import { notificationsSlice } from './slices/notificationsSlice';
import { analyticsSlice } from './slices/analyticsSlice';
import { uiSlice } from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    auth: authSlice.reducer,
    documents: documentsSlice.reducer,
    collaboration: collaborationSlice.reducer,
    workflows: workflowsSlice.reducer,
    notifications: notificationsSlice.reducer,
    analytics: analyticsSlice.reducer,
    ui: uiSlice.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }),
  devTools: process.env.NODE_ENV !== 'production',
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;