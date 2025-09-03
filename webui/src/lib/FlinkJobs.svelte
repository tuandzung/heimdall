<script lang="ts">
  import { format } from "date-fns";
  import Fa from "svelte-fa";
  import {
    faImagePortrait,
    faChartColumn,
    faTable,
    faIdCard,
    faClock,
    faInfo,
    faGear,
  } from "@fortawesome/free-solid-svg-icons";

  import { appConfig, type AppConfig } from "./stores/appConfig";
  import { settings, type SettingsState } from "./stores/settings";
  import {
    flinkJobs,
    type FlinkJobItem,
    type FlinkJobsState,
  } from "./stores/flinkJobs";
  import ExternalEndpoint from "./ExternalEndpoint.svelte";
  import JobType from "./JobType.svelte";
  import Modal from "./Modal.svelte";

  type JobStatus = "RUNNING" | "FAILED" | "FINISHED" | "UNKNOWN" | string;

  interface FlinkResources {
    jm: { replicas: number; cpu: number | string; mem: number | string };
    tm: { replicas: number; cpu: number | string; mem: number | string };
  }

  interface FlinkJob {
    id: string | number;
    name: string;
    status: JobStatus;
    startTime?: number | null;
    resources: FlinkResources;
    type: string;
    parallelism?: number | null;
    flinkVersion?: string | null;
    shortImage?: string | null;
    metadata: Record<string, string>;
  }

  type Sorting =
    | "jobNameAsc"
    | "jobNameDesc"
    | "startTimeAsc"
    | "startTimeDesc"
    | "resourcesAsc"
    | "resourcesDesc";

  let jobNameFilter: string | undefined = $state();
  let statusFilter: JobStatus | undefined = $state();

  let activeSorting: Sorting | undefined = $state();

  let showSettingsModal: boolean = $state(false);

  const visibleFlinkJobs: FlinkJob[] = $derived(
    ((($flinkJobs as FlinkJobsState).data as FlinkJob[]) ?? [])
      .filter((job) => {
        let nameMatch: boolean = true;
        let statusMatch: boolean = true;
        if (jobNameFilter) {
          nameMatch = displayName(job).includes(jobNameFilter);
        }
        if (statusFilter) {
          statusMatch = job.status === statusFilter;
        }
        return nameMatch && statusMatch;
      })
      .sort((a, b) => {
        if (!activeSorting || activeSorting === "jobNameAsc") {
          return sortGeneric(displayName(a), displayName(b));
        } else if (activeSorting === "jobNameDesc") {
          return sortGeneric(displayName(b), displayName(a));
        } else if (activeSorting === "startTimeAsc") {
          return sortNumbers(a.startTime, b.startTime);
        } else if (activeSorting === "startTimeDesc") {
          return sortNumbers(b.startTime, a.startTime);
        } else if (activeSorting === "resourcesAsc") {
          return sortNumbers(totalResources(a), totalResources(b));
        } else if (activeSorting === "resourcesDesc") {
          return sortNumbers(totalResources(b), totalResources(a));
        }
        return 0;
      }),
  );

  const jobStatusList: JobStatus[] = $derived([
    ...new Set(
      ((($flinkJobs as FlinkJobsState).data as FlinkJob[]) ?? []).map(
        (job) => job.status,
      ),
    ),
  ]);

  const displayNamePattern: string | undefined = $derived(
    ($appConfig as AppConfig)?.patterns?.["display-name"] as string | undefined,
  );

  $effect(() => {
    if (($settings as SettingsState).refreshInterval) {
      flinkJobs.setInterval($settings.refreshInterval);
    }
  });

  function statusColor(status: JobStatus): string {
    switch (status) {
      case "RUNNING":
        return "green";
      case "FAILED":
        return "red";
      case "FINISHED":
      case "UNKNOWN":
        return "gray";
      default:
        return "yellow";
    }
  }

  function formatStartTime(startTime: number | null | undefined): string {
    if (startTime == null) return "";
    return format(new Date(startTime), "yyyy-MM-dd HH:mm:ss OOO");
  }

  function displayName(flinkJob: FlinkJob): string {
    const pattern = displayNamePattern ?? "$jobName";
    let name = pattern.replace("$jobName", flinkJob.name);
    if (Object.keys(flinkJob.metadata).length > 0) {
      for (const [key, value] of Object.entries(flinkJob.metadata)) {
        name = name.replace(`$metadata.${key}`, value);
      }
    }
    // clean up metadata that was not found
    if (name.includes("$metadata.")) {
      name = name.replace(/.?\$metadata\.[^ ]*/g, "");
    }
    return name;
  }

  function sortGeneric(a: string, b: string): number {
    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
  }

  function sortNumbers(
    a: number | null | undefined,
    b: number | null | undefined,
  ): number {
    if (a == null) return 1;
    if (b == null) return -1;
    return b - a;
  }

  function totalResources(flinkJob: FlinkJob): number {
    return flinkJob.resources.jm.replicas + flinkJob.resources.tm.replicas;
  }
</script>

<Modal
  showModal={showSettingsModal}
  onClose={() => (showSettingsModal = false)}
>
  {#snippet children()}
    <div>
      Refresh interval:
      <select
        name="refreshInterval"
        bind:value={$settings.refreshInterval}
        class="ml-2"
      >
        <option value="-1">No refresh</option>
        <option value="10">10 sec</option>
        <option value="30">30 sec</option>
        <option value="60">60 sec</option>
        <option value="300">5 min</option>
      </select>
    </div>
    <div class="mt-2.5">
      Display details:
      <div class="mt-1">
        <div>
          <label>
            <input
              name="showJobParallelism"
              type="checkbox"
              bind:checked={$settings.showJobParallelism}
            /> Parallelism
          </label>
        </div>
        <div>
          <label>
            <input
              name="showJobFlinkVersion"
              type="checkbox"
              bind:checked={$settings.showJobFlinkVersion}
            /> Flink version
          </label>
        </div>
        <div>
          <label>
            <input
              name="showJobImage"
              type="checkbox"
              bind:checked={$settings.showJobImage}
            /> Image
          </label>
        </div>
      </div>
    </div>
  {/snippet}
</Modal>
<div class="flex items-center justify-between py-6 text-base">
  <div>
    Filter by name:
    <input
      name="jobNameFilter"
      type="text"
      placeholder="Flink Job name"
      bind:value={jobNameFilter}
    />
    &nbsp; Filter by status
    <select name="statusFilter" bind:value={statusFilter}>
      <option value="">Show all</option>
      {#each jobStatusList as status}
        <option value={status}>{status}</option>
      {/each}
    </select>
  </div>
  <div>
    {#if $settings.displayMode === "card"}
      <button
        type="button"
        title="Table view"
        onclick={() => ($settings.displayMode = "tabular")}
        class="inline-block"
      >
        <Fa
          fw
          icon={faTable}
          size="2x"
          class="text-gray-500 hover:cursor-pointer"
        />
      </button>
    {/if}
    {#if $settings.displayMode === "tabular"}
      <button
        type="button"
        title="Card view"
        onclick={() => ($settings.displayMode = "card")}
        class="inline-block"
      >
        <Fa
          fw
          icon={faIdCard}
          size="2x"
          class="text-gray-500 hover:cursor-pointer"
        />
      </button>
    {/if}
    <button
      type="button"
      title="Settings"
      onclick={() => (showSettingsModal = true)}
      class="inline-block"
    >
      <Fa
        fw
        icon={faGear}
        size="2x"
        class="text-gray-500 hover:cursor-pointer ml-1"
      />
    </button>
  </div>
</div>

{#if ($flinkJobs as FlinkJobsState).error}
  <p class="text-xl text-center text-red-500 font-bold">
    Couldn't load data: {($flinkJobs as FlinkJobsState).error}
  </p>
{:else if visibleFlinkJobs.length > 0 || jobNameFilter || statusFilter}
  {#if $settings.displayMode === "tabular"}
    <table class="table-auto w-full border">
      <thead class="text-lg">
        <tr class="bg-slate-50">
          <th class="border border-slate-300 p-2 w-4/12">
            <div class="flex items-center justify-center">
              Flink Job
              <div class="flex flex-col ml-2">
                <button
                  aria-label="Sort by name ascending"
                  class="h-0 w-0 border-x-8 border-x-transparent border-b-10 hover:cursor-pointer mb-1"
                  onclick={() => (activeSorting = "jobNameAsc")}
                  class:border-b-black={activeSorting !== "jobNameAsc"}
                  class:border-b-[#e6516f]={activeSorting === "jobNameAsc"}
                ></button>
                <button
                  aria-label="Sort by name descending"
                  class="h-0 w-0 border-x-8 border-x-transparent border-t-10 hover:cursor-pointer"
                  onclick={() => (activeSorting = "jobNameDesc")}
                  class:border-t-black={activeSorting !== "jobNameDesc"}
                  class:border-t-[#e6516f]={activeSorting === "jobNameDesc"}
                ></button>
              </div>
            </div>
          </th>
          <th class="border border-slate-300 p-2 w-1/12">Status</th>
          <th class="border border-slate-300 p-2 w-3/12">
            <div class="flex items-center justify-center">
              Resources
              <div class="flex flex-col ml-2">
                <button
                  aria-label="Sort by resources ascending"
                  class="h-0 w-0 border-x-8 border-x-transparent border-b-10 border-b-black hover:cursor-pointer mb-1"
                  onclick={() => (activeSorting = "resourcesAsc")}
                  class:border-b-black={activeSorting !== "resourcesAsc"}
                  class:border-b-[#e6516f]={activeSorting === "resourcesAsc"}
                ></button>
                <button
                  aria-label="Sort by resources descending"
                  class="h-0 w-0 border-x-8 border-x-transparent border-t-10 border-t-black hover:cursor-pointer"
                  onclick={() => (activeSorting = "resourcesDesc")}
                  class:border-t-black={activeSorting !== "resourcesDesc"}
                  class:border-t-[#e6516f]={activeSorting === "resourcesDesc"}
                ></button>
              </div>
            </div>
          </th>
          <th class="border border-slate-300 p-2 w-2/12">
            <div class="flex items-center justify-center">
              Started At
              <div class="flex flex-col ml-2">
                <button
                  aria-label="Sort by start time ascending"
                  class="h-0 w-0 border-x-8 border-x-transparent border-b-10 border-b-black hover:cursor-pointer mb-1"
                  onclick={() => (activeSorting = "startTimeAsc")}
                  class:border-b-black={activeSorting !== "startTimeAsc"}
                  class:border-b-[#e6516f]={activeSorting === "startTimeAsc"}
                ></button>
                <button
                  aria-label="Sort by start time descending"
                  class="h-0 w-0 border-x-8 border-x-transparent border-t-10 border-t-black hover:cursor-pointer"
                  onclick={() => (activeSorting = "startTimeDesc")}
                  class:border-t-black={activeSorting !== "startTimeDesc"}
                  class:border-t-[#e6516f]={activeSorting === "startTimeDesc"}
                ></button>
              </div>
            </div>
          </th>
          <th class="border border-slate-300 p-2 w-2/12">Endpoints</th>
        </tr>
      </thead>
      <tbody class="text-base">
        {#each visibleFlinkJobs as flinkJob (flinkJob.id)}
          <tr class="odd:bg-white even:bg-slate-50">
            <td class="border border-slate-300 p-2">
              <div class="flex items-start justify-between text-lg">
                <div>
                  <p>{displayName(flinkJob)}</p>
                  {#if $settings.showJobParallelism}
                    <p class="text-sm text-gray-500">
                      <Fa fw icon={faChartColumn} /> Parallelism: {flinkJob.parallelism ||
                        "N/A"}
                    </p>
                  {/if}
                  {#if $settings.showJobFlinkVersion && flinkJob.flinkVersion}
                    <p class="text-sm text-gray-500">
                      <Fa fw icon={faInfo} /> Flink version: {flinkJob.flinkVersion}
                    </p>
                  {/if}
                  {#if $settings.showJobImage}
                    <p class="text-sm text-gray-500">
                      <Fa fw icon={faImagePortrait} /> Image: {flinkJob.shortImage ||
                        "N/A"}
                    </p>
                  {/if}
                </div>
                <div>
                  <JobType type={flinkJob.type} />
                </div>
              </div>
            </td>
            <td class="border border-slate-300 p-2">
              <div class="flex items-center">
                <div
                  class="mr-1.5 w-4 h-4 rounded-full bg-{statusColor(
                    flinkJob.status,
                  )}-500"
                ></div>
                {flinkJob.status}
              </div>
            </td>
            <td class="border border-slate-300 p-2">
              <p>
                JobManager{#if flinkJob.resources.jm.replicas > 1}s{/if}:
                <strong>{flinkJob.resources.jm.replicas}</strong> x {flinkJob
                  .resources.jm.cpu} cpu, {flinkJob.resources.jm.mem} memory
              </p>
              {#if flinkJob.resources.tm.replicas > 0}
                <p>
                  TaskManager{#if flinkJob.resources.tm.replicas > 1}s{/if}:
                  <strong>{flinkJob.resources.tm.replicas}</strong> x {flinkJob
                    .resources.tm.cpu} cpu, {flinkJob.resources.tm.mem} memory
                </p>
              {/if}
            </td>
            <td class="border border-slate-300 p-2"
              >{formatStartTime(flinkJob.startTime)}</td
            >
            <td class="border border-slate-300 p-2">
              <p>
                <ExternalEndpoint
                  type="flink-ui"
                  title="Flink UI"
                  jobName={flinkJob.name}
                />
                <ExternalEndpoint
                  type="flink-api"
                  title="Flink API"
                  jobName={flinkJob.name}
                />
              </p>
              <p>
                <ExternalEndpoint
                  type="metrics"
                  title="Metrics"
                  jobName={flinkJob.name}
                />
                <ExternalEndpoint
                  type="logs"
                  title="Logs"
                  jobName={flinkJob.name}
                />
              </p>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {:else}
    <div class="grid gap-6 grid-cols-3">
      {#each visibleFlinkJobs as flinkJob (flinkJob.id)}
        <div class="border border-slate-300 p-2">
          <div class="flex items-start justify-between pb-4 text-lg">
            <p>{displayName(flinkJob)}</p>
            <JobType type={flinkJob.type} />
          </div>
          <div class="flex items-center pb-4">
            <div
              class="mr-1.5 w-4 h-4 rounded-full bg-{statusColor(
                flinkJob.status,
              )}-500"
            ></div>
            {flinkJob.status}
          </div>
          <div class="pb-4">
            {#if $settings.showJobParallelism}
              <p class="text-sm text-gray-500">
                <Fa fw icon={faChartColumn} /> Parallelism: {flinkJob.parallelism ||
                  "N/A"}
              </p>
            {/if}
            <p class="text-sm text-gray-500">
              <Fa fw icon={faClock} /> Started at: {formatStartTime(
                flinkJob.startTime,
              )}
            </p>
            {#if $settings.showJobFlinkVersion && flinkJob.flinkVersion}
              <p class="text-sm text-gray-500">
                <Fa fw icon={faInfo} /> Flink version: {flinkJob.flinkVersion}
              </p>
            {/if}
            {#if $settings.showJobImage}
              <p class="text-sm text-gray-500">
                <Fa fw icon={faImagePortrait} /> Image: {flinkJob.shortImage ||
                  "N/A"}
              </p>
            {/if}
          </div>
          <p>
            <ExternalEndpoint
              type="flink-ui"
              title="Flink UI"
              jobName={flinkJob.name}
            />
            <ExternalEndpoint
              type="flink-api"
              title="Flink API"
              jobName={flinkJob.name}
            />
            <ExternalEndpoint
              type="metrics"
              title="Metrics"
              jobName={flinkJob.name}
            />
            <ExternalEndpoint
              type="logs"
              title="Logs"
              jobName={flinkJob.name}
            />
          </p>
        </div>
      {/each}
    </div>
  {/if}
{:else if ($flinkJobs as FlinkJobsState).loaded}
  <p class="text-xl text-center font-bold">No Flink Jobs found</p>
{:else}
  <p class="text-xl text-center font-bold">Loading...</p>
{/if}
