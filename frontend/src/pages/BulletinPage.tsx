import { ArrowLeft, Printer } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useForecastPanchayat, usePanchayatAdvisories } from "../api/hooks";
import { LANGS, type Lang } from "../api/types";
import { QueryBoundary } from "../components/QueryBoundary";
import { SegmentedControl } from "../components/SegmentedControl";
import { publishedInOrder } from "../features/farmer/farmerData";
import { tempText, rainText } from "../features/farmer/forecastText";
import { formatDate, formatNumber } from "../lib/format";
import { LANG_OPTIONS } from "../lib/langs";
import { pickText } from "../lib/text";
import { useAppStore } from "../state/store";

const MAX_ACTIONS = 4;
const SUMMARY_DAYS = 3;

/**
 * Printable A4 Panchayat bulletin (Guide 7.1): Panchayat, date, 3-day summary, up to four
 * approved actions with reasons, a data status line, the officer-review note, and the mock
 * notice in the footer. Black-and-white safe: words and borders, no fills. The bulletin's
 * language comes from ?lang= and does not change the app's language.
 */
export default function BulletinPage() {
  const { i18n, t: tApp } = useTranslation();
  const { pid = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const appLang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const q = params.get("lang");
  const lang: Lang = LANGS.includes(q as Lang) ? (q as Lang) : appLang;
  const t = i18n.getFixedT(lang);
  const forecast = useForecastPanchayat(pid, issueDate);
  const advisories = usePanchayatAdvisories(pid, issueDate);

  const setLang = (next: Lang) => {
    const p = new URLSearchParams(params);
    p.set("lang", next);
    setParams(p, { replace: true });
  };

  return (
    <main id="main" tabIndex={-1} className="bulletin-screen">
      <div className="toolbar bulletin-toolbar">
        <Link to={{ pathname: "/farmer", search: issueDate ? `?date=${issueDate}` : "" }}>
          <ArrowLeft size={16} aria-hidden="true" />
          {tApp("bulletin.back")}
        </Link>
        <SegmentedControl
          legend={tApp("bulletin.language")}
          name="bulletin-lang"
          value={lang}
          options={LANG_OPTIONS}
          onChange={setLang}
        />
        <button type="button" className="btn btn-primary" onClick={() => window.print()}>
          <Printer size={16} aria-hidden="true" />
          {tApp("bulletin.print")}
        </button>
      </div>

      <article className="bulletin" lang={lang}>
        <QueryBoundary query={forecast} what={tApp("what.forecastPanchayat")}>
          {(f) => {
            const days = f.days.slice(0, SUMMARY_DAYS);
            return (
              <>
                <header className="bulletin-head">
                  <p className="bulletin-kicker">
                    {t("app.name")} · {t("bulletin.heading")}
                  </p>
                  <h1>
                    {t(f.name.includes(f.panchayat_id) ? "bulletin.placeNamed" : "bulletin.place", {
                      name: f.name,
                      pid: f.panchayat_id,
                      block: f.block_id,
                    })}
                  </h1>
                  <p>{t("bulletin.issued", { date: formatDate(f.issue_date, lang) })}</p>
                </header>

                <section aria-labelledby="b-summary">
                  <h2 id="b-summary">{t("bulletin.summaryTitle")}</h2>
                  <table className="bulletin-table">
                    <thead>
                      <tr>
                        <th scope="col">{t("bulletin.day")}</th>
                        {days.map((d) => (
                          <th key={d.date} scope="col" className="bulletin-day">
                            {formatDate(d.date, lang, "day")}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <th scope="row">{t("farmer.rain")}</th>
                        {days.map((d) => (
                          <td key={d.date}>{rainText(d, lang, t)}</td>
                        ))}
                      </tr>
                      <tr>
                        <th scope="row">{t("farmer.temp")}</th>
                        {days.map((d) => (
                          <td key={d.date}>{tempText(d, lang, t)}</td>
                        ))}
                      </tr>
                      <tr>
                        <th scope="row">{t("farmer.wind")}</th>
                        {days.map((d) => (
                          <td key={d.date}>
                            {t("farmer.windValue", { value: formatNumber(d.wind.p50, lang, 0) })}
                          </td>
                        ))}
                      </tr>
                      <tr>
                        <th scope="row">{t("farmer.spray")}</th>
                        {days.map((d) => {
                          const r = d.derived.spray_rating;
                          return <td key={d.date}>{r ? t(`farmer.sprayHelp.${r}`) : "–"}</td>;
                        })}
                      </tr>
                    </tbody>
                  </table>
                  <p className="bulletin-note">{t("farmer.sprayNote")}</p>
                </section>

                <section aria-labelledby="b-actions">
                  <h2 id="b-actions">{t("bulletin.actionsTitle")}</h2>
                  <QueryBoundary query={advisories} what={tApp("what.bulletinAdvice")}>
                    {(list) => {
                      const items = publishedInOrder(list.items);
                      if (!items.length) return <p>{t("bulletin.noActions")}</p>;
                      const extra = items.length - MAX_ACTIONS;
                      return (
                        <>
                          <ol className="bulletin-actions">
                            {items.slice(0, MAX_ACTIONS).map((a) => {
                              const action = pickText(a.action, lang);
                              const reason = a.reason[action.lang] ?? a.reason.en;
                              const crop =
                                a.crop === "livestock"
                                  ? t("crops.livestock")
                                  : t(`crops.${a.crop}`, { defaultValue: a.crop });
                              return (
                                <li key={a.id} className="bulletin-day">
                                  <p className="bulletin-action" lang={action.lang}>
                                    <span className="bulletin-crop">{crop}: </span>
                                    {action.text}
                                  </p>
                                  <p lang={action.lang}>{t("bulletin.why", { reason })}</p>
                                </li>
                              );
                            })}
                          </ol>
                          {extra > 0 ? <p>{t("bulletin.moreActions", { count: extra })}</p> : null}
                        </>
                      );
                    }}
                  </QueryBoundary>
                </section>

                <footer className="bulletin-foot">
                  <p>{t("bulletin.reviewed")}</p>
                  <p>
                    {t("bulletin.dataStatus", {
                      model: f.model_version ?? "–",
                      date: formatDate(f.issue_date, lang),
                    })}
                    {lang !== "en" ? ` ${t("bulletin.translationNote")}` : ""}
                  </p>
                  {f.data_mode === "mock" ? (
                    <p className="bulletin-mock">{t("shell.ribbon")}</p>
                  ) : null}
                </footer>
              </>
            );
          }}
        </QueryBoundary>
      </article>
    </main>
  );
}
