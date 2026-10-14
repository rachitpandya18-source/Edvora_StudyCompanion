import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import settingsApi from '../api/settingsApi';

export default function SettingsPage({
  user,
  recentCourses = [],
  onNavigate,
  onBackToDashboard,
  onLogout,
}) {
  const [settings, setSettings] = useState(null);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [isSavingKey, setIsSavingKey] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const loadSettings = () => {
    settingsApi.getSettings()
      .then((data) => {
        setSettings(data);
      })
      .catch((err) => {
        console.warn('Failed to load settings:', err);
      });
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSaveApiKey = async (e) => {
    e.preventDefault();
    const clean = apiKeyInput.trim();
    if (!clean) {
      showToast('Please enter an API key.');
      return;
    }
    if (clean.length < 15) {
      showToast('Gemini API key must be at least 15 characters long.');
      return;
    }

    setIsSavingKey(true);
    setTestResult(null);
    try {
      await settingsApi.updateGeminiKey(clean);
      showToast('Gemini API key saved and activated successfully!');
      setApiKeyInput('');
      loadSettings();
    } catch (err) {
      showToast(err.message || 'Failed to update API key.');
    } finally {
      setIsSavingKey(false);
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await settingsApi.testGeminiConnection();
      setTestResult(res);
      if (res.success) {
        showToast('Gemini connection verified successfully!');
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: err.message || 'Connection test failed.',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const isConfigured = Boolean(settings?.gemini_configured);

  return (
    <AppLayout
      activeNav="settings"
      onNavigate={onNavigate}
      user={user}
      recentCourses={recentCourses}
    >
      <div className="p-6 sm:p-8 lg:p-10 max-w-4xl mx-auto w-full space-y-8 animate-fadeIn">
        {/* Toast Alert */}
        {toastMessage && (
          <div className="fixed bottom-6 right-6 z-50 bg-[#18181c] border border-[#a78bfa]/50 text-white text-xs px-4 py-2.5 rounded-lg shadow-xl flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#34d399]" />
            <span>{toastMessage}</span>
          </div>
        )}

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[#222227]">
          <div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onBackToDashboard}
                className="p-1 rounded-lg text-[#71717a] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
                title="Back to Dashboard"
              >
                <span className="material-symbols-outlined text-[20px]">arrow_back</span>
              </button>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                Settings
              </h1>
            </div>
            <p className="text-sm text-[#a1a1aa] mt-1 ml-8">
              Manage your AI configuration, educational settings, and workspace preferences.
            </p>
          </div>
        </div>

        {/* 1. AI ENGINE SETTINGS */}
        <section className="p-6 rounded-2xl bg-[#121215] border border-[#27272a] space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#18181b] border border-[#27272a] flex items-center justify-center text-[#a78bfa]">
                <span className="material-symbols-outlined text-[20px]">psychology</span>
              </div>
              <div>
                <h2 className="text-base font-semibold text-white">
                  Google Gemini AI Engine
                </h2>
                <p className="text-xs text-[#a1a1aa]">
                  Powers curriculum graph generation, AI tutor synthesis, and question generation.
                </p>
              </div>
            </div>

            {/* Status Pill */}
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${
                  isConfigured
                    ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30'
                    : 'bg-zinc-800/80 text-zinc-300 border-zinc-700/50'
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isConfigured ? 'bg-emerald-400' : 'bg-zinc-400'
                  }`}
                />
                {isConfigured ? 'Live Gemini AI Active' : 'Offline Grounded Mode (Deterministic)'}
              </span>
            </div>
          </div>

          {/* Model Info Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-[#09090b] border border-[#27272a]">
              <span className="text-[11px] font-mono text-[#71717a] uppercase tracking-wider block">
                Primary Model
              </span>
              <span className="text-sm font-semibold text-white mt-1 block">
                {settings?.gemini_primary_model || 'gemini-2.5-flash'}
              </span>
              <span className="text-[11px] text-[#a1a1aa] mt-0.5 block">
                Ultra-fast academic analysis & multi-turn reasoning.
              </span>
            </div>

            <div className="p-4 rounded-xl bg-[#09090b] border border-[#27272a]">
              <span className="text-[11px] font-mono text-[#71717a] uppercase tracking-wider block">
                Fallback Model
              </span>
              <span className="text-sm font-semibold text-white mt-1 block">
                {settings?.gemini_fallback_model || 'gemini-1.5-flash'}
              </span>
              <span className="text-[11px] text-[#a1a1aa] mt-0.5 block">
                Automatic fallback on rate limits or service retries.
              </span>
            </div>
          </div>

          {/* API Key Form */}
          <form onSubmit={handleSaveApiKey} className="space-y-3 pt-2 border-t border-[#222227]">
            <label className="text-xs font-semibold text-white block">
              Gemini API Key
              {settings?.api_key_hint && (
                <span className="ml-2 text-[11px] font-mono text-[#71717a]">
                  (Current: {settings.api_key_hint})
                </span>
              )}
            </label>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              <div className="relative flex-1">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  placeholder={isConfigured ? 'Enter new key to update...' : 'AIzaSy...'}
                  className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-[#52525b] focus:border-[#a78bfa] focus:outline-none pr-10 font-mono text-xs"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#71717a] hover:text-white transition-colors cursor-pointer"
                  title={showKey ? 'Hide key' : 'Show key'}
                >
                  <span className="material-symbols-outlined text-[18px]">
                    {showKey ? 'visibility_off' : 'visibility'}
                  </span>
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="submit"
                  disabled={isSavingKey || !apiKeyInput.trim()}
                  className="px-4 py-2.5 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50 shrink-0 inline-flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-sm">
                    {isSavingKey ? 'sync' : 'check'}
                  </span>
                  <span>{isSavingKey ? 'Saving...' : 'Save Key'}</span>
                </button>

                <button
                  type="button"
                  disabled={isTesting || !isConfigured}
                  onClick={handleTestConnection}
                  title={!isConfigured ? 'Configure a valid Gemini API key to test connection' : 'Test Gemini connection'}
                  className="px-4 py-2.5 rounded-lg bg-[#18181b] hover:bg-[#202026] border border-[#27272a] hover:border-[#a78bfa]/50 text-white text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50 shrink-0 inline-flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-sm text-[#a78bfa]">
                    {isTesting ? 'sync' : 'bolt'}
                  </span>
                  <span>{isTesting ? 'Testing...' : 'Test Connection'}</span>
                </button>
              </div>
            </div>

            {testResult && (
              <div
                className={`p-3 rounded-lg border text-xs flex items-center gap-2 ${
                  testResult.success
                    ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                    : 'bg-red-950/40 border-red-500/40 text-red-300'
                }`}
              >
                <span className="material-symbols-outlined text-base">
                  {testResult.success ? 'check_circle' : 'error'}
                </span>
                <span>{testResult.message}</span>
              </div>
            )}

            <p className="text-[11px] text-[#71717a] leading-relaxed">
              Edvora supports both live Google Gemini models and an offline deterministic grounded curriculum generator. Get a free API key at{' '}
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-[#a78bfa] hover:underline font-medium"
              >
                Google AI Studio
              </a>
              .
            </p>
          </form>
        </section>

        {/* 2. ACADEMIC & ADAPTIVE PREFERENCES */}
        <section className="p-6 rounded-2xl bg-[#121215] border border-[#27272a] space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#18181b] border border-[#27272a] flex items-center justify-center text-[#a78bfa]">
              <span className="material-symbols-outlined text-[20px]">tune</span>
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">
                Study & Adaptive Engine Preferences
              </h2>
              <p className="text-xs text-[#a1a1aa]">
                Control default question counts and adaptive mastery calibration.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div className="p-4 rounded-xl bg-[#09090b] border border-[#27272a] space-y-2">
              <label className="text-xs font-semibold text-white block">
                Practice Session Length
              </label>
              <select
                defaultValue="5"
                className="w-full bg-[#121215] border border-[#27272a] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#a78bfa]"
              >
                <option value="3">Quick (3 questions · ~5 mins)</option>
                <option value="5">Standard (5 questions · ~8 mins)</option>
                <option value="10">Comprehensive (10 questions · ~15 mins)</option>
              </select>
            </div>

            <div className="p-4 rounded-xl bg-[#09090b] border border-[#27272a] space-y-2">
              <label className="text-xs font-semibold text-white block">
                BKT Mastery Threshold
              </label>
              <select
                defaultValue="0.80"
                className="w-full bg-[#121215] border border-[#27272a] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#a78bfa]"
              >
                <option value="0.70">Developing (0.70)</option>
                <option value="0.80">Standard Mastered (0.80)</option>
                <option value="0.90">High Mastery Calibration (0.90)</option>
              </select>
            </div>
          </div>
        </section>

        {/* 3. STUDENT PROFILE & ACCOUNT */}
        <section className="p-6 rounded-2xl bg-[#121215] border border-[#27272a] space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#202026] text-[#a78bfa] border border-[#2e2e36] flex items-center justify-center font-mono font-medium text-sm">
                {user?.initials || (user?.name || user?.full_name || 'ST').slice(0, 2).toUpperCase()}
              </div>
              <div>
                <h2 className="text-base font-semibold text-white">
                  {user?.name || user?.full_name || user?.username || 'Student'}
                </h2>
                <p className="text-xs text-[#a1a1aa]">
                  {user?.email || 'student@university.edu'}{user?.program ? ` · ${user.program}` : ''}
                </p>
              </div>
            </div>

            {onLogout && (
              <button
                type="button"
                onClick={onLogout}
                className="px-4 py-2 rounded-lg bg-red-950/40 hover:bg-red-900/60 border border-red-500/40 text-red-300 text-xs font-semibold transition-colors cursor-pointer inline-flex items-center gap-1.5"
              >
                <span className="material-symbols-outlined text-sm">logout</span>
                <span>Sign Out</span>
              </button>
            )}
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
