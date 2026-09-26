import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { useAppStore, type Role } from "../state/store";
import { SegmentedControl } from "./SegmentedControl";

/**
 * Officer / Farmer. Only changes the layout: there is no login in the prototype.
 * The URL query (date, var, pid) is kept when switching.
 */
export function RoleSwitch() {
  const { t } = useTranslation();
  const role = useAppStore((s) => s.role);
  const navigate = useNavigate();
  const { search } = useLocation();
  const onChange = (next: Role) => {
    navigate({ pathname: next === "farmer" ? "/farmer" : "/map", search });
  };
  return (
    <SegmentedControl
      legend={t("shell.role")}
      name="role"
      value={role}
      options={[
        { value: "officer", label: t("shell.officer") },
        { value: "farmer", label: t("shell.farmer") },
      ]}
      onChange={onChange}
    />
  );
}
