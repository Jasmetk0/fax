import { useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import SquashEnginePlayerGrowthPage from "./pages/SquashEnginePlayerGrowthPage";

const playerGrowthPath = "/squash-engine/player-growth";

function Navbar() {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleDropdown = () => setDropdownOpen((open) => !open);
  const closeDropdown = () => setDropdownOpen(false);
  const toggleMobile = () => setMobileOpen((open) => !open);

  return (
    <header className="navbar">
      <div className="navbar-logo">FAX Browser</div>
      <nav className="nav-links" onMouseLeave={closeDropdown}>
        <NavLink to="/" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} end>
          Domů
        </NavLink>
        <div className={`nav-dropdown${dropdownOpen ? " open" : ""}`}>
          <button type="button" onClick={toggleDropdown} aria-haspopup="true" aria-expanded={dropdownOpen}>
            SquashEngine ▾
          </button>
          {dropdownOpen ? (
            <div className="nav-dropdown-menu" role="menu">
              <NavLink
                to={playerGrowthPath}
                className={({ isActive }) => `${isActive ? "active " : ""}nav-link`}
                onClick={closeDropdown}
              >
                Player Growth
              </NavLink>
            </div>
          ) : null}
        </div>
      </nav>
      <button type="button" className="nav-mobile-toggle" onClick={toggleMobile} aria-expanded={mobileOpen}>
        ☰
      </button>
      {mobileOpen ? (
        <div className="nav-mobile">
          <NavLink to="/" onClick={() => setMobileOpen(false)} className={({ isActive }) => (isActive ? "active" : undefined)}>
            Domů
          </NavLink>
          <NavLink
            to={playerGrowthPath}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            SquashEngine · Player Growth
          </NavLink>
        </div>
      ) : null}
    </header>
  );
}

export default function App() {
  return (
    <>
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path={playerGrowthPath} element={<SquashEnginePlayerGrowthPage />} />
        </Routes>
      </main>
    </>
  );
}
