import { readable } from "svelte/store";
import axios from "axios";

export interface AppConfig {
  appVersion?: string;
  patterns?: Record<string, string>;
  endpointPathPatterns?: Record<string, string>;
}

export const appConfig = readable<AppConfig | null>(null, function start(set) {
  axios
    .get("api/config")
    .then((response) => {
      set(response.data as AppConfig);
    })
    .catch((error) => {
      // TODO: proper error handling/logging
      console.log(error);
    });

  return function stop() {};
});
