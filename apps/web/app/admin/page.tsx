import type { Metadata } from "next";

import { AdminAccountManager } from "../../components/AdminAccountManager";

export const metadata: Metadata = {
  title: "账号管理 | SignalTutor",
};

export default function AdminPage() {
  return <AdminAccountManager />;
}
