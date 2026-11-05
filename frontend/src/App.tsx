import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/AppLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import MyListsPage from "@/pages/MyListsPage";
import ProfilePage from "@/pages/ProfilePage";
import RegisterPage from "@/pages/RegisterPage";
import SearchPage from "@/pages/SearchPage";
import TitlePage from "@/pages/TitlePage";
import { useAuth } from "@/stores/auth";

function PublicOnly({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  if (auth.status === "authenticated") return <Navigate to="/" replace />;
  return <>{children}</>;
}

function Protected({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <AppLayout>{children}</AppLayout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicOnly>
            <LoginPage />
          </PublicOnly>
        }
      />
      <Route
        path="/register"
        element={
          <PublicOnly>
            <RegisterPage />
          </PublicOnly>
        }
      />
      <Route path="/" element={<Protected><HomePage /></Protected>} />
      <Route path="/search" element={<Protected><SearchPage /></Protected>} />
      <Route path="/lists" element={<Protected><MyListsPage /></Protected>} />
      <Route path="/profile" element={<Protected><ProfilePage /></Protected>} />
      <Route
        path="/title/:provider/:mediaType/:externalId"
        element={<Protected><TitlePage /></Protected>}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
