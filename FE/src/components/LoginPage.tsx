import { useState } from 'react';
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const handleSuccess = async (response: CredentialResponse) => {
    if (!response.credential) {
      setError('No credential received from Google');
      return;
    }
    try {
      setError(null);
      await login(response.credential);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#0f172a]">
      <div className="bg-[#16213e] border border-[#334155] rounded-2xl p-8 w-full max-w-sm text-center shadow-lg">
        <h1 className="text-2xl font-bold text-[#e2e8f0] uppercase tracking-wider mb-2">
          SLM Lab
        </h1>
        <p className="text-[#94a3b8] text-sm mb-8">
          Sign in to start chatting
        </p>
        <div className="flex justify-center mb-4">
          <GoogleLogin
            onSuccess={handleSuccess}
            onError={() => setError('Google sign-in failed. Please verify that VITE_GOOGLE_CLIENT_ID is correctly configured.')}
            theme="filled_black"
            size="large"
            width="300"
          />
        </div>
        {error && (
          <p className="text-[#ef4444] text-sm mt-4">{error}</p>
        )}
      </div>
    </div>
  );
}
