import {mockApi} from "./mock-api";
import {mockScenarios, type MockScenario} from "./scenarios";

export function MockToolbar({onChange}: {onChange: () => void}) {
  if (!(import.meta.env.DEV && import.meta.env.VITE_MOCK === "1")) return null;
  return (
    <div className="mock-toolbar">
      <b>Xem thử</b>
      <select
        value={mockApi.scenario}
        onChange={(event) => {
          mockApi.setScenario(event.target.value as MockScenario);
          onChange();
        }}
      >
        {mockScenarios.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
      </select>
    </div>
  );
}
