import type { TFunction } from "i18next";
import type { Advisory } from "../../api/types";

/** Advisory title: "Spray: Cotton, boll development and picking"; livestock has no crop. */
export function advisoryTitle(
  t: TFunction,
  a: Pick<Advisory, "crop" | "stage" | "category">,
): string {
  const category = t(`categories.${a.category}`);
  return a.crop === a.category ? category : `${category}: ${cropStage(t, a)}`;
}

/** "Cotton, boll development and picking" in the UI language. */
export function cropStage(t: TFunction, a: Pick<Advisory, "crop" | "stage">): string {
  const crop = t(`crops.${a.crop}`, { defaultValue: a.crop });
  return a.stage
    ? t("review.cropStage", {
        crop,
        stage: t(`stages.${a.stage}`, { defaultValue: a.stage.replaceAll("_", " ") }),
      })
    : crop;
}

/** Short name of an advisory for lists and toasts: "MP0301 cotton spray". */
export function shortName(
  t: TFunction,
  a: Pick<Advisory, "panchayat_id" | "crop" | "category">,
): string {
  if (a.crop === a.category) {
    return t("review.shortNameNoCrop", {
      pid: a.panchayat_id,
      category: t(`categories.${a.category}`),
    });
  }
  return t("review.shortName", {
    pid: a.panchayat_id,
    crop: t(`crops.${a.crop}`, { defaultValue: a.crop }),
    category: t(`categories.${a.category}`),
  });
}

/**
 * A Panchayat's name with its id, without repeating the id when the name already has it
 * (the synthetic names do: "Synthetic Panchayat MP0101").
 */
export function placeLabel(name: string, pid: string): { name: string; id: string | null } {
  return { name, id: name.includes(pid) ? null : pid };
}
