import { useTranslation } from "react-i18next";
import { useAppStore } from "../state/store";
import { LANG_OPTIONS } from "../lib/langs";
import { SegmentedControl } from "./SegmentedControl";

export function LangSwitch() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const setLang = useAppStore((s) => s.setLang);
  return (
    <SegmentedControl
      legend={t("shell.language")}
      name="lang"
      value={lang}
      options={LANG_OPTIONS}
      onChange={setLang}
    />
  );
}
