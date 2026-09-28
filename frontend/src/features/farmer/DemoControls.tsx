import { useId } from "react";
import { Settings2 } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { apiGet } from "../../api/client";
import { queryKeys } from "../../api/hooks";
import type { Farmer } from "../../api/types";
import { IssueDateSelect } from "../../components/IssueDateSelect";
import { DEMO_FARMER_IDS } from "../../lib/config";
import { sharedSearch } from "../../state/urlState";
import { useAppStore } from "../../state/store";

/**
 * Small developer control, clearly labelled as demo: pick one of the five demo farmers and
 * the issue date. Choosing a farmer also switches to that farmer's language.
 */
export function DemoControls() {
  const { t } = useTranslation();
  const id = useId();
  const client = useQueryClient();
  const { search } = useLocation();
  const farmerId = useAppStore((s) => s.farmerId);
  const setFarmerId = useAppStore((s) => s.setFarmerId);
  const setLang = useAppStore((s) => s.setLang);

  const choose = async (next: string) => {
    setFarmerId(next);
    try {
      const f = await client.fetchQuery({
        queryKey: queryKeys.farmer(next),
        queryFn: () => apiGet<Farmer>(`/farmers/${next}`),
      });
      setLang(f.language);
    } catch {
      // The screen shows the error; the language stays as it is.
    }
  };

  return (
    <details className="demo-controls">
      <summary>
        <Settings2 size={16} aria-hidden="true" />
        {t("demo.summary")}
      </summary>
      <div className="demo-controls-body">
        <p className="small">{t("demo.note")}</p>
        <div className="field-inline">
          <label htmlFor={id}>{t("demo.farmer")}</label>
          <select id={id} value={farmerId} onChange={(e) => void choose(e.target.value)}>
            {DEMO_FARMER_IDS.map((fid, i) => (
              <option key={fid} value={fid}>
                {t("demo.farmerOption", { n: i + 1, id: fid })}
              </option>
            ))}
          </select>
        </div>
        <IssueDateSelect />
        <Link to={{ pathname: "/map", search: sharedSearch(search) }}>{t("demo.officer")}</Link>
      </div>
    </details>
  );
}
