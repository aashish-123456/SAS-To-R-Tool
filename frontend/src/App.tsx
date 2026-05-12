import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import NewProject from './pages/NewProject';
import ProjectWorkflow from './pages/ProjectWorkflow';
import Settings from './pages/Settings';
import MyProfile from './pages/MyProfile';
import Login from './pages/Login';
import SignUp from './pages/SignUp';
import ForgotPassword from './pages/ForgotPassword';
import './index.css';

const queryClient = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } } });
const IDLE_TIMEOUT_MS = 5 * 60 * 1000;

function SessionManager() {
  useEffect(() => {
    const markActive = () => {
      if (localStorage.getItem('isAuthenticated') === 'true') {
        localStorage.setItem('lastActivityAt', String(Date.now()));
      }
    };
    const events: Array<keyof WindowEventMap> = ['click', 'keydown', 'mousemove', 'scroll'];
    events.forEach((e) => window.addEventListener(e, markActive, { passive: true }));
    const timer = window.setInterval(() => {
      const isAuth = localStorage.getItem('isAuthenticated') === 'true';
      if (!isAuth) return;
      const last = Number(localStorage.getItem('lastActivityAt') || 0);
      if (!last || Date.now() - last > IDLE_TIMEOUT_MS) {
        localStorage.removeItem('isAuthenticated');
        localStorage.removeItem('authToken');
        localStorage.removeItem('lastActivityAt');
        window.location.href = '/login';
      }
    }, 15000);
    markActive();
    return () => {
      events.forEach((e) => window.removeEventListener(e, markActive));
      window.clearInterval(timer);
    };
  }, []);
  return null;
}

function App() {
  const isAuthenticated = localStorage.getItem('isAuthenticated') === 'true';
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <SessionManager />
        <Routes>
          <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="*" element={!isAuthenticated ? <Navigate to="/login" replace /> : <Layout><Routes><Route path="/" element={<Navigate to="/dashboard" replace />} /><Route path="/dashboard" element={<Dashboard />} /><Route path="/projects" element={<Projects />} /><Route path="/projects/new" element={<NewProject />} /><Route path="/projects/:projectId/*" element={<ProjectWorkflow />} /><Route path="/settings" element={<Settings />} /><Route path="/profile" element={<MyProfile />} /></Routes></Layout>} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
