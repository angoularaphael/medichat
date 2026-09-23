import {
  Activity,
  HeartPulse,
  LayoutDashboard,
  Leaf,
  LogOut,
  Orbit,
  Radio,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const navItems = [
  { to: "/dashboard", label: "Mission", icon: LayoutDashboard },
  { to: "/consultation", label: "Medichat", icon: HeartPulse },
  { to: "/cultures", label: "Cultures", icon: Leaf },
  { to: "/surveillance", label: "Veille", icon: Activity },
  { to: "/journal", label: "Journal", icon: Radio },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="mission-shell">
      <div className="star-layer stars-a" aria-hidden="true" />
      <div className="star-layer stars-b" aria-hidden="true" />
      <aside className="nav-rail">
        <NavLink className="brand-mark" to="/dashboard" aria-label="EIR Medichat">
          <Orbit size={24} />
          <span>EIR</span>
        </NavLink>
        <nav aria-label="Navigation principale">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : "")}>
              <Icon size={20} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <button className="nav-logout" type="button" onClick={logout}>
          <LogOut size={19} />
          <span>Quitter</span>
        </button>
      </aside>

      <div className="mission-main">
        <header className="topbar">
          <div>
            <span className="eyebrow">Yggdrasil / Unite medicale orbitale</span>
            <strong>Poste EIR-07</strong>
          </div>
          <div className="topbar-status">
            <span className="signal latency">
              <i />
              Lien Terre latent
            </span>
            <button className="profile-launch" type="button" onClick={() => navigate("/profil")}>
              <div className="avatar">
                {user?.avatar_data ? <img src={user.avatar_data} alt="" /> : user?.full_name.slice(0, 1)}
              </div>
              <div className="identity">
                <strong>{user?.full_name}</strong>
                <span>{user?.role === "admin" ? "Commandant medical" : "Membre equipage"}</span>
              </div>
            </button>
          </div>
        </header>

        <div className="medical-notice">
          <Activity size={16} />
          Lien Terre lent et instable. EIR decide a bord sans attendre; un message sol part en file.
        </div>

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
