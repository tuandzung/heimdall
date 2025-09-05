import { writable } from "svelte/store";

export interface SettingsState {
  refreshInterval: string; // seconds as string
  displayMode: "tabular" | "card";
  showJobParallelism: boolean;
  showJobFlinkVersion: boolean;
  showJobImage: boolean;
}

const defaults: SettingsState = {
  refreshInterval: "30", // FIXME
  displayMode: "tabular",
  showJobParallelism: true,
  showJobFlinkVersion: true,
  showJobImage: true
};

const storedRaw = typeof localStorage !== "undefined" ? localStorage.getItem("heimdall_settings") : null;
const stored: SettingsState | null = storedRaw
  ? (() => {
      try {
        return JSON.parse(storedRaw) as SettingsState;
      } catch {
        return null;
      }
    })()
  : null;

export const settings = writable<SettingsState>(stored || defaults);

settings.subscribe((value) => {
  try {
    localStorage.setItem("heimdall_settings", JSON.stringify(value));
  } catch {
    // Ignore localStorage errors
  }
});
