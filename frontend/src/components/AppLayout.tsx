import { type ReactNode } from "react";
import { Library, LogOut, Search, User } from "lucide-react";
import { NavLink } from "react-router-dom";
import { Logo } from "@/components/Logo";
import { useAuth } from "@/stores/auth";

type NavItemProps = {
  to: string;
  label: string;
  icon: ReactNode;
};

function NavItem({ to, label, icon }: NavItemProps) {
  return (
    <NavLink
      to={to}
      title={label}
      aria-label={label}
      className={({ isActive }) =>
        [
          "flex h-11 w-11 items-center justify-center rounded-field transition",
          isActive
            ? "bg-accent-soft text-accent-dark"
            : "text-muted hover:bg-row hover:text-accent-dark",
        ].join(" ")
      }
    >
      {icon}
    </NavLink>
  );
}

export function AppLayout({ children }: { children: ReactNode }) {
  const auth = useAuth();

  return (
    <div className="flex min-h-screen bg-bg">
      <aside className="flex w-[72px] shrink-0 flex-col items-center justify-between border-r border-line bg-sidebar py-5">
        <NavLink
          to="/"
          aria-label="MediaTrack"
          className="flex h-11 w-11 items-center justify-center text-accent-dark"
        >
          <Logo size={22} />
        </NavLink>

        <nav className="flex flex-col items-center gap-2">
          <NavItem to="/search" label="Пошук" icon={<Search size={20} />} />
          <NavItem to="/lists" label="Мої списки" icon={<Library size={20} />} />
          <NavItem to="/profile" label="Профіль" icon={<User size={20} />} />
        </nav>

        <button
          type="button"
          onClick={() => void auth.logout()}
          aria-label="Вийти"
          title="Вийти"
          className="flex h-11 w-11 items-center justify-center rounded-field text-muted transition hover:bg-row hover:text-error"
        >
          <LogOut size={20} />
        </button>
      </aside>

      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
