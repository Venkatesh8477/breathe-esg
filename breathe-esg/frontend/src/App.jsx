import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './auth'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'
import ReviewPage from './pages/ReviewPage'
import RecordDetailPage from './pages/RecordDetailPage'
import Layout from './components/Layout'

function PrivateRoute({ children }) {
  const { user } = useAuth()
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="review" element={<ReviewPage />} />
        <Route path="records/:id" element={<RecordDetailPage />} />
      </Route>
    </Routes>
  )
}
