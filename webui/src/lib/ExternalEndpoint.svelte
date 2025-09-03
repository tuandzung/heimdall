<script lang="ts">
  import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
  import Fa from "svelte-fa";

  import { appConfig, type AppConfig } from "./stores/appConfig";

  interface Props {
    jobName: string;
    type: string;
    title: string;
  }

  let { jobName, type, title }: Props = $props();

  const endpointPathPattern: string | undefined = $derived(
    ($appConfig as AppConfig)?.endpointPathPatterns?.[type] as
      | string
      | undefined,
  );

  function processEndpointPathPattern(
    pattern: string,
    jobName: string,
  ): string {
    return pattern.replace("$jobName", jobName);
  }
</script>

{#if endpointPathPattern}
  <a
    href={processEndpointPathPattern(endpointPathPattern, jobName)}
    target="_blank"
    rel="noreferrer noopener"
    class="text-blue-600 mr-1"
  >
    {title}
    <Fa fw icon={faArrowUpRightFromSquare} />
  </a>
{/if}
