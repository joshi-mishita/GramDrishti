import { TriangleAlert } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Provenance } from "../api/types";

/** Says where the numbers on a screen come from when they are not computed results. */
export function ProvenanceNote({ provenance }: { provenance: Provenance }) {
  const { t } = useTranslation();
  if (provenance === "computed") return null;
  return (
    <p className="provenance">
      <TriangleAlert size={16} aria-hidden="true" />
      <span>{t(`provenance.${provenance}`)}</span>
    </p>
  );
}
