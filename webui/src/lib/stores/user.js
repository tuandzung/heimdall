import { writable } from "svelte/store";
import axios from "axios";
import { getToken, setToken, clearToken } from "../auth.js";

function createUserStore() {
	const { subscribe, set } = writable({ user: null, loaded: false });

	async function refresh() {
		try {
			const resp = await axios.get("/users/me");
			set({ user: resp.data, loaded: true });
		} catch (e) {
			set({ user: null, loaded: true });
		}
	}

	async function logout() {
		try {
			// For JWT, clearing the token is enough; POST is still safe for legacy session
			await axios.post("/auth/logout");
		} finally {
			// Ensure local state is cleared and force a UI reload
			clearToken();
			set({ user: null, loaded: true });
			if (typeof window !== "undefined" && window.location) {
				window.location.href = "/";
			}
		}
	}

	// On load, if callback redirected with token in URL hash, capture it
	if (typeof window !== "undefined" && window.location) {
		// Capture token provided by backend as URL fragment or search param
		const hash = window.location.hash.startsWith("#")
			? window.location.hash.slice(1)
			: "";
		const hparams = new URLSearchParams(hash);
		let token = hparams.get("token");
		if (!token) {
			const sparams = new URLSearchParams(window.location.search);
			token = sparams.get("token");
			if (token) {
				// Clean search token param
				sparams.delete("token");
				const cleaned =
					window.location.pathname +
					(sparams.toString() ? "?" + sparams.toString() : "");
				window.history.replaceState({}, document.title, cleaned);
			}
		} else {
			// Clean hash
			window.history.replaceState(
				{},
				document.title,
				window.location.pathname + window.location.search,
			);
		}
		if (token) {
			setToken(token);
		}
	}

	// initialize
	const existing = getToken();
	if (existing) {
		axios.defaults.headers.common["Authorization"] = `Bearer ${existing}`;
	}
	refresh();

	return { subscribe, refresh, logout };
}

export const userStore = createUserStore();
