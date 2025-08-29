<script>
  let { type } = $props();
</script>

<p
  class="ml-1 px-1 border border-gray-500 rounded-sm bg-white"
  title="Type: {type}"
>
  {#if type === "APPLICATION"}
    A
  {:else if type === "SESSION"}
    S
  {/if}
</p>
