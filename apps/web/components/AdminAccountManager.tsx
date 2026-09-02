"use client";

import {
  ArrowLeft,
  Check,
  Copy,
  Function,
  Key,
  LockKey,
  Plus,
  Power,
  ShieldCheck,
  User,
} from "@phosphor-icons/react";
import { FormEvent, useState } from "react";

import {
  AdminAccount,
  createAccount,
  listAccounts,
  resetAccountPassword,
  setAccountActive,
} from "../lib/auth";

type IssuedCredential = { username: string; password: string };

export function AdminAccountManager() {
  const [adminKey, setAdminKey] = useState("");
  const [unlocked, setUnlocked] = useState(false);
  const [accounts, setAccounts] = useState<AdminAccount[]>([]);
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [resettingId, setResettingId] = useState<string | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [issued, setIssued] = useState<IssuedCredential | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function unlock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setAccounts(await listAccounts(adminKey));
      setUnlocked(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法进入管理页面");
    } finally {
      setBusy(false);
    }
  }

  async function addAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const next = await createAccount(adminKey, {
        username: username.trim(),
        display_name: displayName.trim(),
        password,
      });
      setAccounts((current) => [next, ...current]);
      setIssued({ username: next.username, password });
      setUsername("");
      setDisplayName("");
      setPassword("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建账号失败");
    } finally {
      setBusy(false);
    }
  }

  async function toggleAccount(account: AdminAccount) {
    setBusy(true);
    setError(null);
    try {
      const next = await setAccountActive(adminKey, account.id, !account.active);
      setAccounts((current) => current.map((item) => item.id === next.id ? next : item));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "更新账号失败");
    } finally {
      setBusy(false);
    }
  }

  async function submitReset(event: FormEvent<HTMLFormElement>, account: AdminAccount) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await resetAccountPassword(adminKey, account.id, resetPassword);
      setIssued({ username: account.username, password: resetPassword });
      setResetPassword("");
      setResettingId(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "重置密码失败");
    } finally {
      setBusy(false);
    }
  }

  if (!unlocked) {
    return (
      <main className="auth-page admin-unlock">
        <section className="auth-panel" aria-labelledby="admin-login-title">
          <div className="auth-brand">
            <span className="brand-symbol"><ShieldCheck size={19} weight="bold" /></span>
            <strong>账号管理</strong>
          </div>
          <div className="auth-copy">
            <h1 id="admin-login-title">管理员验证</h1>
            <p>输入服务器中配置的管理员密钥。</p>
          </div>
          <form className="auth-form" onSubmit={unlock}>
            <label>
              <span>管理员密钥</span>
              <div className="auth-input">
                <Key size={18} />
                <input
                  type="password"
                  value={adminKey}
                  onChange={(event) => setAdminKey(event.target.value)}
                  autoComplete="off"
                  required
                />
              </div>
            </label>
            {error && <p className="auth-error" role="alert">{error}</p>}
            <button className="auth-submit" type="submit" disabled={busy}>
              <span>{busy ? "正在验证" : "进入管理"}</span>
              <LockKey size={18} />
            </button>
          </form>
          <a className="admin-back-link" href="/"><ArrowLeft size={16} />返回学生登录</a>
        </section>
      </main>
    );
  }

  return (
    <main className="admin-page">
      <header className="admin-header">
        <div className="auth-brand">
          <span className="brand-symbol"><Function size={19} weight="bold" /></span>
          <div><strong>SignalTutor</strong><span>学生账号管理</span></div>
        </div>
        <a href="/"><ArrowLeft size={16} />返回学生端</a>
      </header>

      <div className="admin-layout">
        <section className="admin-create" aria-labelledby="create-account-title">
          <h1 id="create-account-title">发放新账号</h1>
          <p>创建后将账号和密码发送给学生。密码不会再次显示。</p>
          <form className="admin-create-form" onSubmit={addAccount}>
            <label><span>账号</span><input value={username} onChange={(event) => setUsername(event.target.value)} pattern="[A-Za-z0-9_.-]+" minLength={3} maxLength={32} required /></label>
            <label><span>学生姓名</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={64} required /></label>
            <label><span>初始密码</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} maxLength={128} required /></label>
            <button type="submit" disabled={busy}><Plus size={17} />创建账号</button>
          </form>
          {issued && (
            <div className="issued-credential" role="status">
              <div><Check size={17} weight="bold" /><strong>账号已准备好</strong></div>
              <code>{issued.username} / {issued.password}</code>
              <button type="button" onClick={() => void navigator.clipboard.writeText(`账号：${issued.username}\n密码：${issued.password}`)}><Copy size={16} />复制</button>
            </div>
          )}
          {error && <p className="auth-error" role="alert">{error}</p>}
        </section>

        <section className="admin-accounts" aria-labelledby="account-list-title">
          <div className="admin-section-title">
            <div><h2 id="account-list-title">已发放账号</h2><p>停用或重置密码后，学生当前登录会立即失效。</p></div>
            <strong>{accounts.length}</strong>
          </div>
          {accounts.length ? (
            <div className="account-list">
              {accounts.map((account) => (
                <article className="account-row" key={account.id}>
                  <div className="account-person">
                    <span><User size={17} /></span>
                    <div><strong>{account.display_name}</strong><code>{account.username}</code></div>
                  </div>
                  <div className="account-actions">
                    <span className={account.active ? "account-status active" : "account-status"}>{account.active ? "可登录" : "已停用"}</span>
                    <button type="button" onClick={() => { setResettingId(account.id); setResetPassword(""); }} disabled={busy}><Key size={15} />重置密码</button>
                    <button type="button" onClick={() => void toggleAccount(account)} disabled={busy}><Power size={15} />{account.active ? "停用" : "启用"}</button>
                  </div>
                  {resettingId === account.id && (
                    <form className="admin-reset-form" onSubmit={(event) => void submitReset(event, account)}>
                      <label><span>新密码</span><input type="password" value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} minLength={8} maxLength={128} autoFocus required /></label>
                      <button type="submit" disabled={busy}>确认重置</button>
                      <button type="button" onClick={() => setResettingId(null)}>取消</button>
                    </form>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <div className="admin-empty"><User size={22} /><span>还没有学生账号</span></div>
          )}
        </section>
      </div>
    </main>
  );
}
