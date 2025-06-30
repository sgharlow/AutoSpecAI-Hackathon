import React, { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import * as monaco from 'monaco-editor';
import { useTheme } from '@mui/material/styles';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { Document } from '../../store/slices/documentsSlice';

interface DocumentEditorProps {
  document: Document;
  isEditing: boolean;
  onContentChange: (content: string) => void;
  readOnly?: boolean;
}

export interface DocumentEditorRef {
  getValue: () => string;
  setValue: (value: string) => void;
  getPosition: () => monaco.Position | null;
  focus: () => void;
}

export const DocumentEditor = forwardRef<DocumentEditorRef, DocumentEditorProps>(
  ({ document, isEditing, onContentChange, readOnly = false }, ref) => {
    const theme = useTheme();
    const { sendDocumentChange, updatePresence } = useWebSocket();
    const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const changeTimeoutRef = useRef<NodeJS.Timeout>();

    useImperativeHandle(ref, () => ({
      getValue: () => editorRef.current?.getValue() || '',
      setValue: (value: string) => editorRef.current?.setValue(value),
      getPosition: () => editorRef.current?.getPosition() || null,
      focus: () => editorRef.current?.focus(),
    }));

    useEffect(() => {
      if (!containerRef.current) return;

      // Configure Monaco Editor
      monaco.editor.defineTheme('autospec-light', {
        base: 'vs',
        inherit: true,
        rules: [
          { token: 'comment', foreground: '6a9955', fontStyle: 'italic' },
          { token: 'keyword', foreground: '0000ff', fontStyle: 'bold' },
          { token: 'string', foreground: 'a31515' },
          { token: 'number', foreground: '098658' },
        ],
        colors: {
          'editor.background': theme.palette.background.paper,
          'editor.foreground': theme.palette.text.primary,
          'editor.lineHighlightBackground': theme.palette.action.hover,
          'editor.selectionBackground': theme.palette.primary.main + '30',
          'editorCursor.foreground': theme.palette.primary.main,
          'editorLineNumber.foreground': theme.palette.text.secondary,
        },
      });

      monaco.editor.defineTheme('autospec-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [
          { token: 'comment', foreground: '6a9955', fontStyle: 'italic' },
          { token: 'keyword', foreground: '569cd6', fontStyle: 'bold' },
          { token: 'string', foreground: 'ce9178' },
          { token: 'number', foreground: 'b5cea8' },
        ],
        colors: {
          'editor.background': theme.palette.background.paper,
          'editor.foreground': theme.palette.text.primary,
          'editor.lineHighlightBackground': theme.palette.action.hover,
          'editor.selectionBackground': theme.palette.primary.main + '30',
          'editorCursor.foreground': theme.palette.primary.main,
          'editorLineNumber.foreground': theme.palette.text.secondary,
        },
      });

      // Create editor instance
      const editor = monaco.editor.create(containerRef.current, {
        value: document.content || '',
        language: getLanguageFromFileType(document.type),
        theme: theme.palette.mode === 'dark' ? 'autospec-dark' : 'autospec-light',
        readOnly: readOnly || !isEditing,
        wordWrap: 'on',
        lineNumbers: 'on',
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        fontSize: 14,
        lineHeight: 20,
        fontFamily: '"Fira Code", "Cascadia Code", "SF Mono", Monaco, "Inconsolata", "Roboto Mono", monospace',
        renderWhitespace: 'selection',
        renderControlCharacters: true,
        contextmenu: true,
        mouseWheelZoom: true,
        smoothScrolling: true,
        cursorBlinking: 'smooth',
        cursorSmoothCaretAnimation: true,
        selectOnLineNumbers: true,
        roundedSelection: false,
        bracketPairColorization: { enabled: true },
        guides: {
          bracketPairs: true,
          indentation: true,
        },
        suggest: {
          showWords: true,
          showSnippets: true,
        },
        quickSuggestions: {
          other: true,
          comments: true,
          strings: true,
        },
      });

      editorRef.current = editor;

      // Handle content changes
      const onContentChangeDisposable = editor.onDidChangeModelContent((e) => {
        const content = editor.getValue();
        onContentChange(content);

        // Debounce sending changes to other collaborators
        clearTimeout(changeTimeoutRef.current);
        changeTimeoutRef.current = setTimeout(() => {
          if (isEditing) {
            sendDocumentChange({
              type: 'content_change',
              changes: e.changes,
              content,
              versionId: e.versionId,
            });
          }
        }, 300);
      });

      // Handle cursor position changes
      const onCursorPositionChangeDisposable = editor.onDidChangeCursorPosition((e) => {
        if (isEditing) {
          updatePresence({
            cursorPosition: {
              lineNumber: e.position.lineNumber,
              column: e.position.column,
            },
            selection: {
              startLineNumber: e.selection.startLineNumber,
              startColumn: e.selection.startColumn,
              endLineNumber: e.selection.endLineNumber,
              endColumn: e.selection.endColumn,
            },
          });
        }
      });

      // Handle focus events
      const onFocusDisposable = editor.onDidFocusEditorText(() => {
        if (isEditing) {
          updatePresence({
            status: 'editing',
            focused: true,
          });
        }
      });

      const onBlurDisposable = editor.onDidBlurEditorText(() => {
        updatePresence({
          status: isEditing ? 'editing' : 'viewing',
          focused: false,
        });
      });

      // Cleanup function
      return () => {
        onContentChangeDisposable.dispose();
        onCursorPositionChangeDisposable.dispose();
        onFocusDisposable.dispose();
        onBlurDisposable.dispose();
        editor.dispose();
        if (changeTimeoutRef.current) {
          clearTimeout(changeTimeoutRef.current);
        }
      };
    }, [document.content, isEditing, readOnly, theme.palette.mode, onContentChange, sendDocumentChange, updatePresence]);

    // Update editor when content changes externally
    useEffect(() => {
      if (editorRef.current && document.content !== undefined) {
        const currentContent = editorRef.current.getValue();
        if (currentContent !== document.content) {
          editorRef.current.setValue(document.content);
        }
      }
    }, [document.content]);

    // Update editor read-only state
    useEffect(() => {
      if (editorRef.current) {
        editorRef.current.updateOptions({ 
          readOnly: readOnly || !isEditing 
        });
      }
    }, [readOnly, isEditing]);

    // Update editor theme
    useEffect(() => {
      if (editorRef.current) {
        monaco.editor.setTheme(theme.palette.mode === 'dark' ? 'autospec-dark' : 'autospec-light');
      }
    }, [theme.palette.mode]);

    const getLanguageFromFileType = (type: string): string => {
      switch (type) {
        case 'pdf':
        case 'txt':
        case 'rtf':
          return 'plaintext';
        case 'docx':
          return 'markdown'; // Treat docx content as markdown for better formatting
        default:
          return 'plaintext';
      }
    };

    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Editor Header */}
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="subtitle2" color="text.secondary">
            {isEditing ? 'Editing' : 'Viewing'} • {document.type.toUpperCase()} • 
            {document.metadata.wordCount ? ` ${document.metadata.wordCount} words` : ''} •
            Last modified: {new Date(document.metadata.lastModified).toLocaleString()}
          </Typography>
        </Box>

        {/* Monaco Editor Container */}
        <Box
          ref={containerRef}
          sx={{
            flex: 1,
            minHeight: 0,
            '& .monaco-editor': {
              height: '100% !important',
            },
            '& .monaco-editor .margin': {
              backgroundColor: 'transparent',
            },
            '& .monaco-editor .monaco-editor-background': {
              backgroundColor: theme.palette.background.paper,
            },
          }}
        />

        {/* Editor Footer */}
        <Box sx={{ p: 1, borderTop: 1, borderColor: 'divider', bgcolor: 'background.default' }}>
          <Typography variant="caption" color="text.secondary">
            {readOnly && 'Read-only mode'} 
            {isEditing && !readOnly && 'Edit mode • Auto-save enabled'}
            {!isEditing && !readOnly && 'View mode • Click Edit to make changes'}
          </Typography>
        </Box>
      </Box>
    );
  }
);