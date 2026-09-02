"use client";

import { Function } from "@phosphor-icons/react";
import { useEffect, useState } from "react";

import { AuthUser, clearAuthToken, fetchCurrentUser, getAuthToken } from "../lib/auth";
import { LoginScreen } from "./LoginScreen";
import { TutorWorkbench } from "./TutorWorkbench";

export function AuthenticatedApp() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const signedOut = () => setUser(null);
    window.addEventListener("signaltutor:unauthorized", signedOut);
    if (!getAuthToken()) {
      setChecking(false);
      return () => window.removeEventListener("signaltutor:unauthorized", signedOut);
    }
    void fetchCurrentUser()
      .then(setUser)
      .catch(() => {
        clearAuthToken();
        setUser(null);
      })
      .finally(() => setChecking(false));
    return () => window.removeEventListener("signaltutor:unauthorized", signedOut);
  }, []);

  if (checking) {
    return (
      <main className="auth-loading" aria-live="polite">
        <span className="welcome-mark"><Function size={22} weight="bold" /></span>
        <span>正在确认登录状态</span>
      </main>
    );
  }

  if (!user) return <LoginScreen onLogin={setUser} />;

  return (
    <TutorWorkbench
      user={user}
      onLogout={() => {
        clearAuthToken();
        setUser(null);
      }}
    />
  );
}
