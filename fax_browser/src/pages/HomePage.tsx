import SquashEnginePlayerGrowthWidget from "../components/widgets/SquashEnginePlayerGrowthWidget";
import useLocalStorage from "../hooks/useLocalStorage";

export default function HomePage() {
  const [widgetEnabled, setWidgetEnabled] = useLocalStorage("se.widget.enabled", true);

  return (
    <section>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ marginBottom: 8 }}>Přehled portálu</h1>
        <p style={{ margin: 0, color: "#64748b" }}>
          Vítejte ve FAX Browseru. Na hlavní stránce můžete přizpůsobit, které widgety budou viditelné.
        </p>
      </header>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="toggle">
          <label htmlFor="se-widget-toggle">Show SquashEngine widget</label>
          <input
            id="se-widget-toggle"
            type="checkbox"
            checked={widgetEnabled}
            onChange={(event) => setWidgetEnabled(event.target.checked)}
          />
        </div>
        <p style={{ marginTop: 12, color: "#64748b", fontSize: 14 }}>
          Nastavení se ukládá do vašeho prohlížeče (localStorage) a zůstane zachováno i po obnovení stránky.
        </p>
      </div>

      <div className="home-grid">
        {widgetEnabled ? <SquashEnginePlayerGrowthWidget /> : null}
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Aktuality portálu</h2>
          <p>
            Najdete zde rychlé odkazy na aktuální sekce portálu, připravované turnaje a novinky z prostředí FAX komunity.
          </p>
          <p style={{ color: "#64748b" }}>
            Přidejte si další widgety nebo skrze hlavní navigaci otevřete plnou stránku SquashEngine Player Growth.
          </p>
        </div>
      </div>
    </section>
  );
}
