import {mockThemeFromUrl} from "../lib/theme";
import {mockApi} from "./mock-api";
import {mockScenarios, type MockScenario} from "./scenarios";
import {useEffect, useState} from "react";

export function MockToolbar({onChange}: {onChange: () => void}) {
  if (!(import.meta.env.DEV && import.meta.env.VITE_MOCK === "1")) return null;
  return (
    <div className="mock-toolbar">
      <b>Xem thử</b>
      <select
        aria-label="Kịch bản xem thử"
        value={mockApi.scenario}
        onChange={(event) => {
          mockApi.setScenario(event.target.value as MockScenario);
          onChange();
        }}
      >
        {mockScenarios.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
      </select>
      <label>
        Theme
        <select
          aria-label="Theme xem thử"
          value={mockThemeFromUrl()}
          onChange={(event) => {
            const url = new URL(window.location.href);
            url.searchParams.set("theme", event.target.value);
            window.history.replaceState(null, "", url);
            window.dispatchEvent(new Event("crv-mock-theme"));
            onChange();
          }}
        >
          <option value="light">Sáng</option>
          <option value="dark">Tối</option>
        </select>
      </label>
      <MockOverflowProbe />
    </div>
  );
}

function MockOverflowProbe() {
  const [state, setState] = useState({ok: "pending", scroll: 0, client: 0});
  useEffect(() => {
    const measure = () => {
      const root = document.documentElement;
      setState({
        ok: root.scrollWidth === root.clientWidth ? "true" : "false",
        scroll: root.scrollWidth,
        client: root.clientWidth,
      });
    };
    const id = window.setTimeout(measure, 250);
    window.addEventListener("resize", measure);
    return () => {
      window.clearTimeout(id);
      window.removeEventListener("resize", measure);
    };
  }, []);
  return <span id="crv-overflow-probe" hidden data-ok={state.ok} data-scroll-width={state.scroll} data-client-width={state.client} />;
}
