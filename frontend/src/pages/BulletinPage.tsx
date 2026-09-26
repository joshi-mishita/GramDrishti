import { Printer } from "lucide-react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/states";

/** Printable A4 Panchayat bulletin (Guide 7.1). Content comes with the bulletin session. */
export default function BulletinPage() {
  const { t } = useTranslation();
  const { pid = "" } = useParams();
  return (
    <div className="page">
      <PageHeader title={t("bulletin.title", { pid })} />
      <EmptyState icon={Printer} title={t("bulletin.notBuilt")} />
    </div>
  );
}
