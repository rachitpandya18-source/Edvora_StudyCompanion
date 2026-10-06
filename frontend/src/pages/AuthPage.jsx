import { useState } from 'react';

export default function AuthPage({
  initialMode = 'login',
  onBackToLanding,
  onAuthSuccess,
}) {
  const [mode, setMode] = useState(initialMode);
  const [showPassword, setShowPassword] = useState(false);
  const [showSignupPassword, setShowSignupPassword] = useState(false);
  const [showSignupConfirm, setShowSignupConfirm] = useState(false);

  // Form states
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirm, setSignupConfirm] = useState('');

  // Feedback status
  const [statusMessage, setStatusMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const switchMode = (newMode) => {
    setMode(newMode);
    setStatusMessage(null);
    setErrorMessage(null);
  };

  const handleLoginSubmit = (e) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);
    setStatusMessage('Signing in...');

    setTimeout(() => {
      setStatusMessage('Success. Entering your Edvora workspace...');
      setTimeout(() => {
        setIsSubmitting(false);
        if (onAuthSuccess) {
          onAuthSuccess({ email: loginEmail, name: loginEmail.split('@')[0] });
        }
      }, 700);
    }, 800);
  };

  const handleSignupSubmit = (e) => {
    e.preventDefault();
    setErrorMessage(null);

    if (signupPassword !== signupConfirm) {
      setErrorMessage('Passwords do not match. Please verify and try again.');
      return;
    }

    if (signupPassword.length < 6) {
      setErrorMessage('Password should be at least 6 characters.');
      return;
    }

    setIsSubmitting(true);
    setStatusMessage('Creating your learning space...');

    setTimeout(() => {
      setStatusMessage('Workspace ready. Entering Edvora...');
      setTimeout(() => {
        setIsSubmitting(false);
        if (onAuthSuccess) {
          onAuthSuccess({ email: signupEmail, name: signupName });
        }
      }, 700);
    }, 900);
  };

  const handleGoogleAuth = () => {
    setIsSubmitting(true);
    setErrorMessage(null);
    setStatusMessage('Connecting with Google...');

    setTimeout(() => {
      setStatusMessage('Authenticated via Google. Entering Edvora...');
      setTimeout(() => {
        setIsSubmitting(false);
        if (onAuthSuccess) {
          onAuthSuccess({ email: 'student@university.edu', name: 'Student' });
        }
      }, 700);
    }, 800);
  };

  return (
    <div className="bg-[#09090b] text-[#fafafa] min-h-screen flex flex-col antialiased selection:bg-primary/30 selection:text-[#fafafa]">
      {/* Top Header */}
      <header className="w-full px-6 py-5 max-w-7xl mx-auto flex items-center justify-between z-10 border-b border-[#27272a]/60">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#18181b] border border-[#27272a] flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-[20px]">school</span>
          </div>
          <span className="font-headline font-bold text-lg tracking-tight text-[#fafafa]">
            EDVORA
          </span>
        </div>

        <button
          type="button"
          onClick={onBackToLanding}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-[#a1a1aa] hover:text-[#fafafa] transition-colors py-1.5 px-3 rounded-lg hover:bg-[#18181b] border border-transparent hover:border-[#27272a] cursor-pointer"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span>
          <span>Back to Edvora</span>
        </button>
      </header>

      {/* Main Content Layout */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-8 md:py-14">
        <div className="w-full max-w-6xl mx-auto grid lg:grid-cols-12 gap-10 lg:gap-14 items-center">
          
          {/* Left Column: Academic Context & Course Map (Desktop only) */}
          <section className="hidden lg:flex lg:col-span-5 flex-col justify-center space-y-8 pr-4">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#18181b] border border-[#27272a] mb-6">
                <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
                <span className="text-xs font-medium tracking-normal text-[#a1a1aa]">
                  Academic Workspace
                </span>
              </div>

              <h1 className="text-4xl font-bold tracking-tight text-[#fafafa] leading-[1.18]">
                Your course.<br />
                Your companion.<br />
                Your next step.
              </h1>

              <p className="mt-4 text-base leading-relaxed text-[#a1a1aa]">
                Transforming textbooks, slides, and lectures into a continuous, verifiable learning space.
              </p>
            </div>

            {/* Living Course Map Snapshot Card */}
            <div className="p-6 rounded-2xl bg-[#121215] border border-[#27272a] relative overflow-hidden shadow-lg">
              <div className="flex items-center justify-between pb-4 mb-5 border-b border-[#27272a]">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[18px]">account_tree</span>
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#a1a1aa]">
                    Course Knowledge Map
                  </span>
                </div>
                <span className="text-[11px] font-mono text-[#71717a]">CS 201</span>
              </div>

              {/* Connected Nodes */}
              <div className="space-y-0 relative pl-2">
                {/* Node 1: Trees */}
                <div className="flex items-start gap-3.5 relative">
                  <div className="pt-1.5 flex flex-col items-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-primary ring-4 ring-[#121215]"></div>
                    <div className="w-[1.5px] h-10 bg-[#27272a]"></div>
                  </div>
                  <div className="flex-1 bg-[#0f0f12] p-3 rounded-xl border border-[#27272a]/80">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-[#fafafa]">Trees</span>
                      <span className="text-xs font-medium text-primary">62% Mastery</span>
                    </div>
                    <p className="text-xs text-[#a1a1aa] mt-0.5">Hierarchy · Traversals · Grounded</p>
                  </div>
                </div>

                {/* Node 2: AVL Trees */}
                <div className="flex items-start gap-3.5 relative">
                  <div className="pt-1.5 flex flex-col items-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-amber-400 ring-4 ring-[#121215]"></div>
                    <div className="w-[1.5px] h-11 bg-[#27272a]"></div>
                  </div>
                  <div className="flex-1 bg-[#0f0f12] p-3 rounded-xl border border-[#27272a]/80">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-[#fafafa]">AVL Trees</span>
                      <span className="text-xs font-medium text-amber-400">Needs attention · 43%</span>
                    </div>
                    <p className="text-xs text-[#a1a1aa] mt-0.5">Balance factor invariant · Rotations</p>
                  </div>
                </div>

                {/* Recommendation Node: Study next */}
                <div className="flex items-start gap-3.5 pt-1">
                  <div className="pt-2 flex flex-col items-center">
                    <span className="material-symbols-outlined text-[15px] text-tertiary">
                      subdirectory_arrow_right
                    </span>
                  </div>
                  <div className="flex-1 bg-[#18181b]/90 border border-[#27272a] rounded-xl p-3.5">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-tertiary">
                        Study next
                      </span>
                    </div>
                    <p className="text-xs text-[#fafafa] font-medium">
                      Review AVL rotations · Practice 3 questions
                    </p>
                  </div>
                </div>
              </div>

              {/* Card Footer Info */}
              <div className="mt-5 pt-4 border-t border-[#27272a] flex items-center justify-between text-[11px] text-[#a1a1aa]">
                <span className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[14px] text-tertiary">verified</span>
                  Source Grounding: 100% Citation
                </span>
                <span className="font-mono text-[#71717a]">Active Learning</span>
              </div>
            </div>
          </section>

          {/* Right Column: Authentication Card */}
          <section className="lg:col-span-7 flex justify-center">
            <div className="w-full max-w-lg bg-[#121215] border border-[#27272a] rounded-2xl p-6 sm:p-10 shadow-2xl relative">
              
              {/* Mode Switcher Tabs */}
              <div className="w-full grid grid-cols-2 p-1 bg-[#0f0f12] rounded-xl border border-[#27272a] mb-8" role="tablist">
                <button
                  type="button"
                  onClick={() => switchMode('login')}
                  role="tab"
                  aria-selected={mode === 'login'}
                  className={`py-2.5 px-4 rounded-lg text-sm transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer ${
                    mode === 'login'
                      ? 'font-semibold bg-[#18181b] text-[#fafafa] border border-[#27272a]/60 shadow-sm'
                      : 'font-medium text-[#a1a1aa] hover:text-[#fafafa] border border-transparent'
                  }`}
                >
                  <span className="material-symbols-outlined text-[18px]">login</span>
                  <span>Sign in</span>
                </button>
                <button
                  type="button"
                  onClick={() => switchMode('signup')}
                  role="tab"
                  aria-selected={mode === 'signup'}
                  className={`py-2.5 px-4 rounded-lg text-sm transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer ${
                    mode === 'signup'
                      ? 'font-semibold bg-[#18181b] text-[#fafafa] border border-[#27272a]/60 shadow-sm'
                      : 'font-medium text-[#a1a1aa] hover:text-[#fafafa] border border-transparent'
                  }`}
                >
                  <span className="material-symbols-outlined text-[18px]">person_add</span>
                  <span>Create Account</span>
                </button>
              </div>

              {/* LOGIN VIEW */}
              {mode === 'login' && (
                <div className="transition-opacity duration-200">
                  <div className="mb-6">
                    <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#fafafa]">
                      Welcome back.
                    </h2>
                    <p className="text-base text-[#a1a1aa] mt-2">
                      Continue learning with Edvora.
                    </p>
                  </div>

                  {/* Login Form */}
                  <form onSubmit={handleLoginSubmit} className="space-y-5">
                    <div>
                      <label htmlFor="login-email" className="block text-base font-medium text-[#fafafa] mb-2">
                        Email
                      </label>
                      <div className="relative">
                        <input
                          type="email"
                          id="login-email"
                          required
                          value={loginEmail}
                          onChange={(e) => setLoginEmail(e.target.value)}
                          placeholder="Enter your email"
                          className="w-full h-12 px-4 rounded-xl bg-[#18181b] border border-[#27272a] text-base text-[#fafafa] placeholder:text-[#71717a] focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors"
                        />
                        <span className="absolute right-3.5 top-3.5 text-[#a1a1aa] pointer-events-none">
                          <span className="material-symbols-outlined text-[20px]">mail</span>
                        </span>
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label htmlFor="login-password" className="text-base font-medium text-[#fafafa]">
                          Password
                        </label>
                        <button
                          type="button"
                          onClick={() => {
                            setStatusMessage('Password reset link will be sent to your email.');
                          }}
                          className="text-sm font-medium text-primary hover:underline cursor-pointer bg-transparent border-0 p-0"
                        >
                          Forgot password?
                        </button>
                      </div>
                      <div className="relative">
                        <input
                          type={showPassword ? 'text' : 'password'}
                          id="login-password"
                          required
                          value={loginPassword}
                          onChange={(e) => setLoginPassword(e.target.value)}
                          placeholder="Enter your password"
                          className="w-full h-12 pl-4 pr-12 rounded-xl bg-[#18181b] border border-[#27272a] text-base text-[#fafafa] placeholder:text-[#71717a] focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
                          className="absolute right-3 top-2.5 p-1 rounded-lg text-[#a1a1aa] hover:text-[#fafafa] focus:outline-none cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[20px]">
                            {showPassword ? 'visibility_off' : 'visibility'}
                          </span>
                        </button>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full h-12 rounded-xl bg-primary text-[#0a0012] font-semibold text-base hover:opacity-90 active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-2 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-[#09090b] cursor-pointer disabled:opacity-50"
                    >
                      <span>Sign in</span>
                      <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                    </button>
                  </form>

                  {/* Divider */}
                  <div className="relative flex py-3 items-center my-4">
                    <div className="flex-grow border-t border-[#27272a]"></div>
                    <span className="flex-shrink mx-4 text-xs uppercase tracking-wider text-[#a1a1aa] font-mono">
                      or
                    </span>
                    <div className="flex-grow border-t border-[#27272a]"></div>
                  </div>

                  {/* Social Auth: Google */}
                  <button
                    type="button"
                    onClick={handleGoogleAuth}
                    disabled={isSubmitting}
                    className="w-full h-12 rounded-xl bg-[#18181b] border border-[#27272a] hover:bg-[#1e1e22] hover:border-[#52525b] text-base font-medium text-[#fafafa] flex items-center justify-center gap-3 transition-colors mb-6 group focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-[#09090b] cursor-pointer disabled:opacity-50"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"/>
                      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"/>
                      <path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.3 0 12s.7 3.3 1.9 5.7l3.7-2.9z"/>
                      <path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16C3.7 20.4 7.5 23 12 23z"/>
                    </svg>
                    <span>Continue with Google</span>
                  </button>

                  <div className="text-center text-sm text-[#a1a1aa]">
                    Don&apos;t have an account?{' '}
                    <button
                      type="button"
                      onClick={() => switchMode('signup')}
                      className="text-primary font-semibold hover:underline ml-1 cursor-pointer bg-transparent border-0 p-0"
                    >
                      Create one
                    </button>
                  </div>
                </div>
              )}

              {/* SIGN UP VIEW */}
              {mode === 'signup' && (
                <div className="transition-opacity duration-200">
                  <div className="mb-6">
                    <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#fafafa]">
                      Create your learning space.
                    </h2>
                    <p className="text-base text-[#a1a1aa] mt-2">
                      Bring your courses, materials and learning progress into one place.
                    </p>
                  </div>

                  {/* Sign Up Form */}
                  <form onSubmit={handleSignupSubmit} className="space-y-4">
                    <div>
                      <label htmlFor="signup-name" className="block text-base font-medium text-[#fafafa] mb-2">
                        Full name
                      </label>
                      <input
                        type="text"
                        id="signup-name"
                        required
                        value={signupName}
                        onChange={(e) => setSignupName(e.target.value)}
                        placeholder="Enter your name"
                        className="w-full h-12 px-4 rounded-xl bg-[#18181b] border border-[#27272a] text-base text-[#fafafa] placeholder:text-[#71717a] focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors"
                      />
                    </div>

                    <div>
                      <label htmlFor="signup-email" className="block text-base font-medium text-[#fafafa] mb-2">
                        Email
                      </label>
                      <input
                        type="email"
                        id="signup-email"
                        required
                        value={signupEmail}
                        onChange={(e) => setSignupEmail(e.target.value)}
                        placeholder="Enter your email"
                        className="w-full h-12 px-4 rounded-xl bg-[#18181b] border border-[#27272a] text-base text-[#fafafa] placeholder:text-[#71717a] focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors"
                      />
                    </div>

                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label htmlFor="signup-pass" className="block text-base font-medium text-[#fafafa] mb-2">
                          Password
                        </label>
                        <div className="relative">
                          <input
                            type={showSignupPassword ? 'text' : 'password'}
                            id="signup-pass"
                            required
                            value={signupPassword}
                            onChange={(e) => setSignupPassword(e.target.value)}
                            placeholder="Create a password"
                            className="w-full h-12 pl-4 pr-11 rounded-xl bg-[#18181b] border border-[#27272a] text-base text-[#fafafa] placeholder:text-[#71717a] focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors"
                          />
                          <button
                            type="button"
                            onClick={() => setShowSignupPassword(!showSignupPassword)}
                            aria-label={showSignupPassword ? 'Hide password' : 'Show password'}
                            className="absolute right-2.5 top-2.5 p-1 rounded-lg text-[#a1a1aa] hover:text-[#fafafa] focus:outline-none cursor-pointer"
                          >
                            <span className="material-symbols-outlined text-[18px]">
                              {showSignupPassword ? 'visibility_off' : 'visibility'}
                            </span>
                          </button>
                        </div>
                      </div>
                      <div>
                        <label htmlFor="signup-confirm" className="block text-base font-medium text-[#fafafa] mb-2">
                          Confirm password
                        </label>
                        <div className="relative">
                          <input
                            type={showSignupConfirm ? 'text' : 'password'}
                            id="signup-confirm"
                            required
                            value={signupConfirm}
                            onChange={(e) => setSignupConfirm(e.target.value)}
                            placeholder="Confirm your password"
                            className="w-full h-12 pl-4 pr-11 rounded-xl bg-[#18181b] border border-[#27272a] text-base text-[#fafafa] placeholder:text-[#71717a] focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors"
                          />
                          <button
                            type="button"
                            onClick={() => setShowSignupConfirm(!showSignupConfirm)}
                            aria-label={showSignupConfirm ? 'Hide password' : 'Show password'}
                            className="absolute right-2.5 top-2.5 p-1 rounded-lg text-[#a1a1aa] hover:text-[#fafafa] focus:outline-none cursor-pointer"
                          >
                            <span className="material-symbols-outlined text-[18px]">
                              {showSignupConfirm ? 'visibility_off' : 'visibility'}
                            </span>
                          </button>
                        </div>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full h-12 rounded-xl bg-primary text-[#0a0012] font-semibold text-base hover:opacity-90 active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-4 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-[#09090b] cursor-pointer disabled:opacity-50"
                    >
                      <span>Create account</span>
                      <span className="material-symbols-outlined text-[18px]">check</span>
                    </button>
                  </form>

                  {/* Divider */}
                  <div className="relative flex py-3 items-center my-4">
                    <div className="flex-grow border-t border-[#27272a]"></div>
                    <span className="flex-shrink mx-4 text-xs uppercase tracking-wider text-[#a1a1aa] font-mono">
                      or
                    </span>
                    <div className="flex-grow border-t border-[#27272a]"></div>
                  </div>

                  {/* Social Auth: Google */}
                  <button
                    type="button"
                    onClick={handleGoogleAuth}
                    disabled={isSubmitting}
                    className="w-full h-12 rounded-xl bg-[#18181b] border border-[#27272a] hover:bg-[#1e1e22] hover:border-[#52525b] text-base font-medium text-[#fafafa] flex items-center justify-center gap-3 transition-colors mb-6 group focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-[#09090b] cursor-pointer disabled:opacity-50"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"/>
                      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"/>
                      <path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.3 0 12s.7 3.3 1.9 5.7l3.7-2.9z"/>
                      <path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16C3.7 20.4 7.5 23 12 23z"/>
                    </svg>
                    <span>Continue with Google</span>
                  </button>

                  <div className="text-center text-sm text-[#a1a1aa]">
                    Already have an account?{' '}
                    <button
                      type="button"
                      onClick={() => switchMode('login')}
                      className="text-primary font-semibold hover:underline ml-1 cursor-pointer bg-transparent border-0 p-0"
                    >
                      Sign in
                    </button>
                  </div>
                </div>
              )}

              {/* Error Message Toast */}
              {errorMessage && (
                <div className="mt-4 p-3 rounded-xl bg-red-950/70 border border-red-500/50 text-red-200 text-xs font-medium flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-red-400">error</span>
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Status Message Toast */}
              {statusMessage && (
                <div className="mt-4 p-3 rounded-xl bg-tertiary-container border border-tertiary text-emerald-200 text-xs font-medium flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-tertiary">check_circle</span>
                  <span>{statusMessage}</span>
                </div>
              )}

            </div>
          </section>

        </div>
      </main>

      {/* Grounding Footer */}
      <footer className="w-full px-6 py-6 max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-4 text-xs text-[#a1a1aa] border-t border-[#27272a]/50">
        <div className="flex items-center gap-2">
          <span className="font-bold text-[#fafafa]">EDVORA</span>
          <span>•</span>
          <span>Precision in Academic Learning</span>
        </div>
        <div className="flex items-center gap-6">
          <a href="#" onClick={(e) => e.preventDefault()} className="hover:text-primary transition-colors">
            Academic Integrity
          </a>
          <a href="#" onClick={(e) => e.preventDefault()} className="hover:text-primary transition-colors">
            Course Map System
          </a>
          <a href="#" onClick={(e) => e.preventDefault()} className="hover:text-primary transition-colors">
            Privacy
          </a>
        </div>
      </footer>
    </div>
  );
}

