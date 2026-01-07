import React, { useEffect, useState } from 'react';
import { Amplify } from 'aws-amplify';
import {
  fetchAuthSession
} from 'aws-amplify/auth';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import "./output.css";
import { 
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, Legend as RechartsLegend
} from 'recharts';
import { 
    AlertTriangle, ClipboardList, CheckSquare, ShieldCheck 
} from 'lucide-react';
const COLORS = ["#3B82F6", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6"];
// 📦 Configure Amplify with your Cognito info
Amplify.configure({
  Auth: {
    Cognito: {
      region: process.env.REACT_APP_COGNITO_REGION,
      userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID,
      userPoolClientId: process.env.REACT_APP_COGNITO_USER_POOL_CLIENT_ID,
    },
  },
});

// ✅ Real API fetch helper (uses Cognito ID token)
async function apiFetch(path, options = {}) {
  try {
    const { idToken } = (await fetchAuthSession()).tokens ?? {};
    if (!idToken) throw new Error("No valid session found. Please sign in.");

    const headers = new Headers(options.headers || {});
    headers.set('Authorization', `Bearer ${idToken.toString()}`);
    headers.set('Content-Type', 'application/json');

    const res = await fetch(`${process.env.REACT_APP_API_BASE_URL}${path}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
    }

    const contentType = res.headers.get('content-type') || '';
    return contentType.includes('application/json') ? res.json() : res.text();
  } catch (error) {
    console.error("Error in apiFetch:", error);
    throw error;
  }
}


// --- UI Components ---
function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch('/stats');
        // Parse and handle nested body JSON if API wraps data
        console.log(data);
        const parsed =
          typeof data?.body === 'string' ? JSON.parse(data.body) : data;
        setStats(parsed || {});
      } catch (err) {
        console.error('Error loading stats:', err);
        setError(err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading)
    return (
      <div className="flex justify-center items-center h-64 text-gray-400">
        Loading dashboard…
      </div>
    );

  if (error)
    return (
      <div className="p-6 text-red-400 bg-gray-800 rounded-lg">
        Failed to load dashboard data: {error.message}
      </div>
    );

  const keyMetrics = stats?.keyMetrics || {};
  const byStatus = stats?.byStatus || [];
  const byPriority = stats?.byPriority || [];
  const summary = stats?.aiExecutiveSummary || 'No summary available.';

  return (
    <div className="p-6 text-gray-100 space-y-6">
      {/* ---- KEY METRICS CARDS ---- */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          {
            title: 'Total Pending',
            value: keyMetrics.totalPending ?? 0,
            color: 'bg-yellow-500',
          },
          {
            title: 'High Priority',
            value: keyMetrics.highPriority ?? 0,
            color: 'bg-red-500',
          },
          {
            title: 'Total Completed',
            value: keyMetrics.totalCompleted ?? 0,
            color: 'bg-green-500',
          },
        ].map((metric, idx) => (
          <div
            key={idx}
            className={`p-5 rounded-xl shadow-md bg-gray-800 flex flex-col items-center justify-center`}
          >
            <div className={`${metric.color} text-white px-4 py-2 rounded-full font-semibold`}>
              {metric.title}
            </div>
            <div className="text-4xl font-bold mt-3">
              {isNaN(metric.value) ? 0 : metric.value}
            </div>
          </div>
        ))}
      </div>

      {/* ---- CHARTS ---- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <div className="bg-gray-800 rounded-xl p-5 shadow-lg">
          <h3 className="text-lg font-semibold mb-3">Issues by Status</h3>
          {byStatus.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={byStatus}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis dataKey="name" stroke="#ccc" />
                <YAxis stroke="#ccc" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none' }}
                  labelStyle={{ color: '#fff' }}
                />
                <Bar dataKey="value" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400">No status data available.</p>
          )}
        </div>

        {/* Priority Distribution */}
        <div className="bg-gray-800 rounded-xl p-5 shadow-lg">
          <h3 className="text-lg font-semibold mb-3">Issues by Priority</h3>
          {byPriority.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={byPriority}
                  dataKey="value"
                  nameKey="name"
                  outerRadius={100}
                  label
                >
                  {byPriority.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={['#22c55e', '#ef4444', '#f59e0b'][index % 3]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none' }}
                  labelStyle={{ color: '#fff' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400">No priority data available.</p>
          )}
        </div>
      </div>

      {/* ---- EXECUTIVE SUMMARY ---- */}
      <div className="bg-gray-800 rounded-xl p-6 shadow-lg">
        <h3 className="text-lg font-semibold mb-3">AI Executive Summary</h3>
        <div className="whitespace-pre-line text-gray-200 leading-relaxed">
          {summary}
        </div>
      </div>
    </div>
  );
}

function Issues() {
  const [issues, setIssues] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [updating, setUpdating] = useState(false);
  const [status, setStatus] = useState("");
  const [expectedDate, setExpectedDate] = useState("");

  // 🔹 Fetch issues on mount
  // 🔹 Create a reusable function to fetch data
  const fetchIssues = async () => {
    setLoading(true);
    try {
      const data = await apiFetch("/issues");
      const parsed =
        typeof data?.body === "string" ? JSON.parse(data.body) : data;
      setIssues(parsed || []);
      setFiltered(parsed || []); // Also reset filtered list
    } catch (err) {
      console.error("Error fetching issues:", err);
      setIssues([]); // Clear issues on error
      setFiltered([]);
    } finally {
      setLoading(false);
    }
  };

  // 🔹 Fetch issues on mount
  useEffect(() => {
    fetchIssues();
  }, []); // This now calls your new reusable function

  // 🔹 Filter by text input
  useEffect(() => {
    const lower = search.toLowerCase();
    setFiltered(
      issues.filter(
        (i) =>
          i.IssueType?.toLowerCase().includes(lower) ||
          i.UserLocation?.toLowerCase().includes(lower) ||
          i.Status?.toLowerCase().includes(lower) ||
          i.Priority?.toLowerCase().includes(lower)
      )
    );
  }, [search, issues]);

  // 🔹 Open update modal
  const openModal = (issue) => {
    setSelectedIssue(issue);
    setStatus(issue.Status || "New");
    setExpectedDate(issue.ExpectedCompletionDate || "");
  };

  // 🔹 Handle PUT request
  // 🔹 Handle PUT request (Corrected Version)
  const handleUpdate = async () => {
    if (!selectedIssue) return;
    setUpdating(true);
    try {
      // 1. Create the data payload to send
      const updated = {
        ...selectedIssue,
        Status: status,
        ExpectedCompletionDate: expectedDate || "Under Review", // Handle empty date
      };
      
      // 2. Send the update to the backend and wait
      await apiFetch(`/issues/${selectedIssue.IssueID}`, {
        method: "PUT",
        pathParameters:{
            IssueID:selectedIssue.IssueID
        },
        body: JSON.stringify(updated),
      });

      // 3. SUCCESS! Re-fetch the true list from DynamoDB
      // This is the most important change:
      await fetchIssues(); 

      // 4. Close the modal
      setSelectedIssue(null);

    } catch (err) {
      console.error("Error updating issue:", err);
      alert("Failed to update issue. Check console for details.");
    } finally {
      setUpdating(false);
    }
  };

  if (loading)
    return (
      <div className="flex justify-center items-center h-64 text-gray-400">
        Loading issues…
      </div>
    );

  if (!issues.length)
    return (
      <div className="text-gray-300 p-6 bg-gray-800 rounded-md">
        No issues found.
      </div>
    );

  return (
    <div className="p-6 text-gray-100">
      <h2 className="text-xl font-semibold mb-4">Issues Dashboard</h2>

      {/* 🔍 Search bar */}
      <div className="mb-4 flex justify-between items-center">
        <input
          type="text"
          placeholder="Search by type, location, or status…"
          className="px-4 py-2 rounded-md bg-gray-800 text-white border border-gray-700 w-1/2"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* 🧾 Issues Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-700">
        <table className="min-w-full divide-y divide-gray-700 text-sm">
          <thead className="bg-gray-800">
            <tr>
              {[
                "Issue ID",
                "Type",
                "Location",
                "Status",
                "Priority",
                "Expected Completion",
                "Action",
              ].map((head, i) => (
                <th
                  key={i}
                  className="px-4 py-2 text-left font-semibold text-gray-300"
                >
                  {head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {filtered.map((issue) => (
              <tr
                key={issue.IssueID}
                className="hover:bg-gray-800/50 transition"
              >
                <td className="px-4 py-2 font-mono text-xs text-gray-300">
                  {issue.IssueID || "-"}
                </td>
                <td className="px-4 py-2">{issue.IssueType || "-"}</td>
                <td className="px-4 py-2 text-gray-400">
                  {issue.UserLocation || "-"}
                </td>
                <td
                  className={`px-4 py-2 font-semibold ${
                    issue.Status === "Completed"
                      ? "text-green-400"
                      : issue.Status === "Processing"
                      ? "text-yellow-400"
                      : "text-blue-400"
                  }`}
                >
                  {issue.Status || "Unknown"}
                </td>
                <td
                  className={`px-4 py-2 ${
                    issue.Priority === "HIGH"
                      ? "text-red-400"
                      : issue.Priority === "MEDIUM"
                      ? "text-yellow-400"
                      : "text-green-400"
                  }`}
                >
                  {issue.Priority || "-"}
                </td>
                <td className="px-4 py-2">
                  {issue.ExpectedCompletionDate || "—"}
                </td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => openModal(issue)}
                    className="bg-blue-600 hover:bg-blue-500 px-3 py-1 rounded-md text-sm font-semibold"
                  >
                    Update
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 🪟 Update Modal */}
      {selectedIssue && (
        <div className="fixed inset-0 bg-black/70 flex justify-center items-center z-50">
          <div className="bg-gray-900 rounded-lg p-6 w-full max-w-md shadow-lg">
            <h3 className="text-lg font-semibold mb-4">
              Update Issue – {selectedIssue.IssueID}
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">
                  Status
                </label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-white"
                >
                  <option>New</option>
                  <option>Processing</option>
                  <option>Completed</option>
                  <option>Sorting it out</option>
                </select>
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-1">
                  Expected Completion Date
                </label>
                <input
                  type="text"
                  placeholder="e.g. 10 Nov 2025 or 'Under Review'"
                  value={expectedDate}
                  onChange={(e) => setExpectedDate(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-white"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setSelectedIssue(null)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdate}
                disabled={updating}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-md disabled:opacity-50"
              >
                {updating ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


export default function App() {
  const [view, setView] = useState('dashboard');

  return (
    <Authenticator>
      {({ signOut, user }) => (
        <div className="min-h-screen bg-gray-900 text-white">
          <header className="p-4 border-b border-gray-700 flex justify-between items-center">
            <h1 className="text-lg font-semibold">CivicBot Admin</h1>
            <div>
              <span className="mr-4 text-gray-300">{user?.username}</span>
              <button
                onClick={signOut}
                className="bg-red-600 px-3 py-1 rounded-md"
              >
                Sign Out
              </button>
            </div>
          </header>

          <main className="p-6">
            <nav className="mb-4 flex gap-3">
              <button
                onClick={() => setView('dashboard')}
                className={`px-3 py-1 rounded-md ${view === 'dashboard' ? 'bg-blue-600' : 'bg-gray-700'}`}
              >
                Dashboard
              </button>
              <button
                onClick={() => setView('issues')}
                className={`px-3 py-1 rounded-md ${view === 'issues' ? 'bg-blue-600' : 'bg-gray-700'}`}
              >
                Issues
              </button>
            </nav>

            {view === 'dashboard' ? <Dashboard /> : <Issues />}
          </main>
        </div>
      )}
    </Authenticator>
  );
}
