import { writable, type Writable, type Readable } from "svelte/store";
import axios from "axios";

export interface FlinkResources {
  jm: { replicas: number; cpu: number | string; mem: number | string };
  tm: { replicas: number; cpu: number | string; mem: number | string };
}

export interface FlinkJobItem {
  id: string | number;
  name: string;
  status: string;
  startTime?: number | null;
  resources: FlinkResources;
  type: string;
  parallelism?: number | null;
  flinkVersion?: string | null;
  shortImage?: string | null;
  metadata: Record<string, string>;
}

export interface FlinkJobsState {
  data: FlinkJobItem[];
  loaded: boolean;
  error?: unknown;
}

let allFlinkJobs: FlinkJobItem[] = [];

function createDataStore(): Readable<FlinkJobsState> & { setInterval: (intervalSec: string | number) => void } {
  let intervalId: ReturnType<typeof setInterval> | undefined;
  const { set, subscribe }: Writable<FlinkJobsState> = writable({ data: [], loaded: false }, () => {
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  });

  const loadJobs = async (): Promise<void> => {
    try {
      const resp = await axios.get("/api/jobs", { withCredentials: true });
      allFlinkJobs = resp.data as FlinkJobItem[];
      set({
        data: allFlinkJobs,
        error: null,
        loaded: true
      });
    } catch (e) {
      // don't show an error if we already have some loaded jobs
      if (allFlinkJobs.length === 0) {
        set({
          data: allFlinkJobs,
          error: e,
          loaded: true
        });
      }
    }
  };

  loadJobs();

  return {
    subscribe,
    setInterval: (intervalSec: string | number) => {
      const parsed = parseInt(String(intervalSec));
      if (intervalId) clearInterval(intervalId);
      if (parsed > 0) {
        intervalId = setInterval(loadJobs, parsed * 1000);
      }
    }
  };
}

export const flinkJobs = createDataStore();
