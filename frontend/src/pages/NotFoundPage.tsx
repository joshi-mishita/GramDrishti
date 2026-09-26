import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/states";

export default function NotFoundPage() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  return (
    <div className="page">
      <PageHeader title={t("notFound.title")} />
      <EmptyState
        title={t("notFound.body", { path: pathname })}
        action={
          <Link to="/map" className="btn btn-primary">
            {t("notFound.back")}
          </Link>
        }
      />
    </div>
  );
}
