import {useEffect, useState} from "react";
import {api} from "../../api/client";
import {Button} from "../../components/ui";
import type {WorkLocation} from "../../types/api";

export function LocationFilterChips({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (locationId: number | null, location?: WorkLocation | null) => void;
}) {
  const [locations, setLocations] = useState<WorkLocation[]>([]);

  useEffect(() => {
    let active = true;
    api.get<WorkLocation[]>("/locations?active=true")
      .then((rows) => { if (active) setLocations(rows); })
      .catch(() => { if (active) setLocations([]); });
    return () => { active = false; };
  }, []);

  if (locations.length === 0) return null;

  return (
    <div className="location-chip-row" role="list" aria-label="Bộ lọc kho">
      <Button tone={value === null ? "primary" : "secondary"} className="small-button" onClick={() => onChange(null, null)}>Tất cả kho</Button>
      {locations.map((location) => (
        <Button
          key={location.id}
          tone={value === location.id ? "primary" : "secondary"}
          className="small-button"
          onClick={() => onChange(location.id, location)}
        >
          {location.code} · {location.name}
        </Button>
      ))}
    </div>
  );
}
