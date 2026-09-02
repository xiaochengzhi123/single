"use client";

import { ArrowRight, Function, LockKey, User } from "@phosphor-icons/react";
import { FormEvent, useState } from "react";

import { AuthUser, login } from "../lib/auth";

export function LoginScreen({ onLogin }: { onLogin: (user: AuthUser) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      onLogin(await login(username.trim(), password));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "登录失败，请稍后重试");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="login-title">
        <div className="auth-brand">
          <span className="brand-symbol"><Function size={19} weight="bold" /></span>
          <strong>SignalTutor</strong>
        </div>
        <div className="auth-copy">
          <h1 id="login-title">登录后开始学习</h1>
          <p>使用老师发放的账号进入信号与系统考研助手。</p>
        </div>
        <form className="auth-form" onSubmit={submit}>
          <label>
            <span>账号</span>
            <div className="auth-input">
              <User size={18} />
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                minLength={3}
                maxLength={32}
                required
              />
            </div>
          </label>
          <label>
            <span>密码</span>
            <div className="auth-input">
              <LockKey size={18} />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                minLength={8}
                maxLength={128}
                required
              />
            </div>
          </label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" type="submit" disabled={busy}>
            <span>{busy ? "正在登录" : "登录"}</span>
            <ArrowRight size={18} />
          </button>
        </form>
        <p className="auth-help">没有账号请联系老师，不开放自行注册。</p>
      </section>
    </main>
  );
}
