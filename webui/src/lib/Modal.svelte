<script>
  import Fa from "svelte-fa";
  import { faX } from "@fortawesome/free-solid-svg-icons";

  let { showModal, onClose, children } = $props();

  let dialog;

  $effect(() => {
    if (dialog && showModal) dialog.showModal();
  });
</script>

<dialog
  bind:this={dialog}
  onclose={() => onClose?.()}
  onclick={(e) => {
    if (e.target === e.currentTarget) {
      dialog.close();
    }
  }}
  class="w-[500px] h-[200px] p-[25px] outline-hidden fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-lg shadow-lg bg-white border border-gray-200"
>
  <div
    onclick={(e) => e.stopPropagation()}
    onkeydown={(e) => {
      if (e.key === "Escape") {
        dialog.close();
      }
    }}
    role="dialog"
    aria-modal="true"
    tabindex="-1"
  >
    {@render children?.()}
    <div class="absolute top-2 right-2">
      <button
        title="Close"
        onclick={() => dialog.close()}
        class="inline-block bg-transparent border-none cursor-pointer"
        aria-label="Close modal"
      >
        <Fa fw icon={faX} class="text-gray-500 hover:cursor-pointer" />
      </button>
    </div>
  </div>
</dialog>
