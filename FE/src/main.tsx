import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './contexts/AuthContext'
import logger from './utils/logger'

logger.info('[App] Initializing application...');

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {googleClientId ? (
      <GoogleOAuthProvider clientId={googleClientId}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </GoogleOAuthProvider>
    ) : (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', backgroundColor: '#0f172a', color: '#e2e8f0', fontFamily: 'sans-serif' }}>
        <div style={{ maxWidth: '480px', textAlign: 'center', padding: '2rem' }}>
          <h1 style={{ fontSize: '1.5rem', marginBottom: '1rem', color: '#ef4444' }}>Configuration Error</h1>
          <p style={{ marginBottom: '1rem', color: '#94a3b8' }}>
            <code>VITE_GOOGLE_CLIENT_ID</code> is not set. Google Sign-In cannot initialize without it.
          </p>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
            Add <code>VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com</code> to your <code>.env</code> file and restart the dev server.
          </p>
        </div>
      </div>
    )}
  </StrictMode>,
)

logger.info('[App] Application mounted');
