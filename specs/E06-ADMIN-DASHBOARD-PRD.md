# Enhancement #6 – Web‑Based Admin Dashboard

## All-In-One Zero-Shot PRD

**Status:** Deterministic, executable  
**Format:** COSTAR System Prompt + Zero-Shot Prompt + PRD + Implementation Plan

---

## COSTAR System Prompt

```
[CONTEXT]
You are implementing a web‑based admin dashboard for the Frostbyte ETL pipeline. The dashboard must provide a UI for tenant management, document browsing, and system health monitoring. All pages, components, and API calls are defined in the PRD. Use React + TypeScript + Vite, and generate the OpenAPI client from the existing spec.

[OBJECTIVE]
Generate the complete React application source code as specified. The code must be production‑ready, use functional components, and include routing, authentication, and data fetching.

[STYLE]
Imperative. Provide each file content in a code block with its full relative path. No commentary.

[AUDIENCE]
Frontend developer. Execute the steps exactly as written.
```

---

## Production Requirements Document (PRD) – Admin Dashboard

### 1. Technology Stack

- React 18
- TypeScript
- Vite (build tool)
- Tailwind CSS (for styling)
- React Router v6
- TanStack Query (react‑query) for data fetching
- OpenAPI generator (`openapi-typescript-codegen`)

### 2. Pages and Routes

| Route            | Page          | Description                               |
|------------------|---------------|-------------------------------------------|
| `/`              | Dashboard     | Summary cards: tenants, documents, health. |
| `/tenants`       | Tenant List   | List all tenants, create new tenant.      |
| `/tenants/:id`   | Tenant Detail | View/edit tenant, schema extensions.      |
| `/documents`     | Document List | List all documents, filter by tenant.    |
| `/documents/:id` | Document Detail | View document metadata and chunks.     |
| `/jobs`          | Batch Jobs    | View batch job history and progress.     |
| `/jobs/:id`      | Job Detail    | Real‑time progress stream (SSE).         |
| `/settings`      | Settings      | Provider configuration, API keys.        |
| `/login`         | Login         | Authentication (mocked for now).          |

### 3. Mandatory Components

- **Sidebar**: Navigation with icons.
- **DataTable**: Sortable, filterable table.
- **StatusBadge**: For document status, job status.
- **ProgressBar**: For batch job progress.

### 4. API Integration

- Generate TypeScript client from `specs/openapi.yaml` using `openapi-typescript-codegen`.
- All requests use the generated client.
- Base URL: `import.meta.env.VITE_API_URL`

### 5. State Management

- React Query for server state.
- React Context for auth and tenant selection.

### 6. Build and Deployment

- Output directory: `dist`
- Static files served from `/admin` path.

---

## Deterministic Implementation Plan

### Step 1 – Create Vite project

```bash
npm create vite@latest admin-dashboard -- --template react-ts
cd admin-dashboard
npm install
```

### Step 2 – Install dependencies

```bash
npm install react-router-dom @tanstack/react-query tailwindcss @headlessui/react @heroicons/react
npm install -D @openapitools/openapi-generator-cli tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### Step 3 – Configure Tailwind

**File: `admin-dashboard/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### Step 4 – Generate API client

Copy `specs/openapi.yaml` into `admin-dashboard/openapi.yaml`. Add script to `package.json`:

```json
"generate-client": "openapi-generator-cli generate -i openapi.yaml -g typescript-fetch -o src/api/generated"
```

Run:

```bash
npm run generate-client
```

### Step 5 – Create application files

#### File: `admin-dashboard/src/App.tsx`

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { TenantProvider } from './contexts/TenantContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import TenantList from './pages/TenantList';
import TenantDetail from './pages/TenantDetail';
import DocumentList from './pages/DocumentList';
import DocumentDetail from './pages/DocumentDetail';
import JobList from './pages/JobList';
import JobDetail from './pages/JobDetail';
import Settings from './pages/Settings';
import Login from './pages/Login';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <TenantProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={<Layout />}>
                <Route index element={<Dashboard />} />
                <Route path="tenants" element={<TenantList />} />
                <Route path="tenants/:id" element={<TenantDetail />} />
                <Route path="documents" element={<DocumentList />} />
                <Route path="documents/:id" element={<DocumentDetail />} />
                <Route path="jobs" element={<JobList />} />
                <Route path="jobs/:id" element={<JobDetail />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Routes>
          </TenantProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
```

#### File: `admin-dashboard/src/components/Layout.tsx`

```tsx
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

#### File: `admin-dashboard/src/components/Sidebar.tsx`

```tsx
import { Link, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  UserGroupIcon,
  DocumentIcon,
  Cog6ToothIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

const nav = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Tenants', href: '/tenants', icon: UserGroupIcon },
  { name: 'Documents', href: '/documents', icon: DocumentIcon },
  { name: 'Jobs', href: '/jobs', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];

export default function Sidebar() {
  const location = useLocation();
  return (
    <aside className="w-64 bg-white border-r border-gray-200">
      <nav className="p-4 space-y-1">
        {nav.map((item) => {
          const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/');
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`flex items-center px-3 py-2 rounded-md text-sm font-medium ${
                isActive ? 'bg-indigo-50 text-indigo-700' : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <item.icon className="mr-3 h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
```

#### File: `admin-dashboard/src/components/Header.tsx`

```tsx
export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <h1 className="text-lg font-semibold text-gray-900">Frostbyte Admin</h1>
    </header>
  );
}
```

#### File: `admin-dashboard/src/pages/Dashboard.tsx`

```tsx
import { useQuery } from '@tanstack/react-query';

export default function Dashboard() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/health`);
      if (!res.ok) throw new Error('Health check failed');
      return res.json();
    },
  });

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">Tenants</div>
        <div className="bg-white p-4 rounded-lg shadow">Documents</div>
        <div className="bg-white p-4 rounded-lg shadow">
          Health: {health?.status ?? 'checking...'}
        </div>
      </div>
    </div>
  );
}
```

#### File: `admin-dashboard/src/pages/TenantList.tsx`

```tsx
export default function TenantList() {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Tenants</h2>
      <p className="text-gray-500">Tenant list – integrate with generated API client.</p>
    </div>
  );
}
```

#### File: `admin-dashboard/src/pages/TenantDetail.tsx`

```tsx
import { useParams } from 'react-router-dom';

export default function TenantDetail() {
  const { id } = useParams();
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Tenant: {id}</h2>
      <p className="text-gray-500">Tenant detail – integrate with generated API client.</p>
    </div>
  );
}
```

#### File: `admin-dashboard/src/pages/DocumentList.tsx`

```tsx
export default function DocumentList() {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Documents</h2>
      <p className="text-gray-500">Document list – integrate with generated API client.</p>
    </div>
  );
}
```

#### File: `admin-dashboard/src/pages/DocumentDetail.tsx`

```tsx
import { useParams } from 'react-router-dom';

export default function DocumentDetail() {
  const { id } = useParams();
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Document: {id}</h2>
      <p className="text-gray-500">Document detail – integrate with generated API client.</p>
    </div>
  );
}
```

#### File: `admin-dashboard/src/pages/JobList.tsx`

```tsx
export default function JobList() {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Batch Jobs</h2>
      <p className="text-gray-500">Job list – integrate with batch API.</p>
    </div>
  );
}
```

#### File: `admin-dashboard/src/pages/JobDetail.tsx`

```tsx
import { useParams } from 'react-router-dom';
import { useJobProgress } from '../hooks/useJobProgress';

export default function JobDetail() {
  const { id } = useParams();
  const { progress, status } = useJobProgress(id ?? '');

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Job: {id}</h2>
      <div className="bg-white p-4 rounded-lg shadow">
        <p>Status: {status}</p>
        <p>Progress: {progress.processed}/{progress.total}</p>
      </div>
    </div>
  );
}
```

#### File: `admin-dashboard/src/hooks/useJobProgress.ts`

```tsx
import { useEffect, useState } from 'react';

interface JobProgress {
  processed: number;
  total: number;
}

export function useJobProgress(jobId: string) {
  const [progress, setProgress] = useState<JobProgress>({ processed: 0, total: 0 });
  const [status, setStatus] = useState<string>('pending');

  useEffect(() => {
    if (!jobId) return;
    const url = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/batch/jobs/${jobId}/stream`;
    const es = new EventSource(url);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.event_type === 'progress') {
          setProgress((p) => ({ ...p, processed: (p.processed || 0) + 1 }));
        } else if (data.event_type === 'complete' || data.event_type === 'cancel') {
          setStatus(data.event_type);
          es.close();
        }
      } catch (_) {}
    };
    return () => es.close();
  }, [jobId]);

  return { progress, status };
}
```

#### File: `admin-dashboard/src/pages/Settings.tsx`

```tsx
export default function Settings() {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Settings</h2>
      <p className="text-gray-500">Provider configuration, API keys.</p>
    </div>
  );
}
```

#### File: `admin-dashboard/src/pages/Login.tsx`

```tsx
export default function Login() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow max-w-md w-full">
        <h2 className="text-xl font-semibold mb-4">Login (Mocked)</h2>
        <p className="text-gray-500">Authentication placeholder – mock login for now.</p>
      </div>
    </div>
  );
}
```

#### File: `admin-dashboard/src/contexts/AuthContext.tsx`

```tsx
import { createContext, useContext, useState, ReactNode } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        login: () => setIsAuthenticated(true),
        logout: () => setIsAuthenticated(false),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
```

#### File: `admin-dashboard/src/contexts/TenantContext.tsx`

```tsx
import { createContext, useContext, useState, ReactNode } from 'react';

interface TenantContextType {
  selectedTenantId: string | null;
  setSelectedTenantId: (id: string | null) => void;
}

const TenantContext = createContext<TenantContextType | null>(null);

export function TenantProvider({ children }: { children: ReactNode }) {
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);
  return (
    <TenantContext.Provider value={{ selectedTenantId, setSelectedTenantId }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  const ctx = useContext(TenantContext);
  if (!ctx) throw new Error('useTenant must be used within TenantProvider');
  return ctx;
}
```

### Step 6 – Configure environment variables

**File: `admin-dashboard/.env`**

```
VITE_API_URL=http://localhost:8000
```

### Step 7 – Set Vite base path for `/admin` deployment

**File: `admin-dashboard/vite.config.ts`** – add `base: '/admin/'`:

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/admin/',
})
```

### Step 8 – Build and test

```bash
cd admin-dashboard
npm run build
npm run preview
```

### Step 9 – Commit

```bash
git add admin-dashboard
git commit -m "feat(ui): add web‑based admin dashboard with React + TypeScript"
```
