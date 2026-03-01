/** Dashboard — shown after successful Face ID authentication. */

import { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { api } from '../services/api';

interface SystemStatus {
  status: string;
  services: Record<string, string>;
}

export function Dashboard() {
  const { username, userId, logout } = useAuthStore();
  const [users, setUsers] = useState<
    Array<{
      id: string;
      username: string;
      full_name?: string;
      enrollment_count: number;
      created_at?: string;
    }>
  >([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [usersData, healthData] = await Promise.all([
        api.listUsers(),
        api.health(),
      ]);
      setUsers(usersData);
      setSystemStatus(healthData);
    } catch (e) {
      console.error('Failed to load dashboard data:', e);
    }
  }

  const statusColor = (s: string) => {
    if (s === 'ok') return 'text-green-400';
    if (s === 'degraded') return 'text-yellow-400';
    return 'text-red-400';
  };

  const statusDot = (s: string) => {
    if (s === 'ok') return 'bg-green-400';
    if (s === 'unavailable') return 'bg-red-400';
    return 'bg-yellow-400';
  };

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-gray-400">
              Welcome, <span className="text-blue-400">{username}</span>
            </p>
          </div>
          <button onClick={logout} className="btn-secondary text-sm">
            Logout
          </button>
        </div>

        {/* System Status */}
        {systemStatus && (
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">System Status</h2>
            <div className="flex items-center gap-2 mb-4">
              <span className={`font-medium ${statusColor(systemStatus.status)}`}>
                {systemStatus.status.toUpperCase()}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(systemStatus.services).map(([name, status]) => (
                <div
                  key={name}
                  className="bg-gray-800/50 rounded-xl p-4 flex items-center gap-3"
                >
                  <div className={`w-3 h-3 rounded-full ${statusDot(status)}`} />
                  <div>
                    <div className="text-sm font-medium capitalize">{name}</div>
                    <div className="text-xs text-gray-500">{status}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* User info */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Your Profile</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-800/50 rounded-xl p-4">
              <div className="text-sm text-gray-400">Username</div>
              <div className="text-lg font-medium">{username}</div>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-4">
              <div className="text-sm text-gray-400">User ID</div>
              <div className="text-sm font-mono text-gray-300">
                {userId?.slice(0, 8)}...
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-4">
              <div className="text-sm text-gray-400">Auth Method</div>
              <div className="text-lg font-medium text-blue-400">Face ID</div>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-4">
              <div className="text-sm text-gray-400">Status</div>
              <div className="text-lg font-medium text-green-400">Active</div>
            </div>
          </div>
        </div>

        {/* Enrolled users */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">
            Enrolled Users ({users.length})
          </h2>
          {users.length === 0 ? (
            <p className="text-gray-500 text-sm">No enrolled users yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-400 border-b border-gray-800">
                    <th className="text-left py-2 px-3">Username</th>
                    <th className="text-left py-2 px-3">Full Name</th>
                    <th className="text-center py-2 px-3">Enrollments</th>
                    <th className="text-left py-2 px-3">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr
                      key={user.id}
                      className="border-b border-gray-800/50 hover:bg-gray-800/30"
                    >
                      <td className="py-2 px-3 font-medium">{user.username}</td>
                      <td className="py-2 px-3 text-gray-400">
                        {user.full_name || '—'}
                      </td>
                      <td className="py-2 px-3 text-center">
                        {user.enrollment_count}
                      </td>
                      <td className="py-2 px-3 text-gray-500 text-xs">
                        {user.created_at
                          ? new Date(user.created_at).toLocaleDateString()
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
