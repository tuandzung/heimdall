import axios from "axios";

export async function startGoogleOAuth(): Promise<void> {
  // Use cookie-based OAuth so the session is kept in a secure cookie
  const resp = await axios.get("/auth/google-cookie/authorize", {
    params: { scopes: ["openid", "email", "profile"] },
    // Keep the signature compatible with Axios' expected serializer param type
    paramsSerializer: (params: Record<string, string | string[] | undefined>) => {
      const usp = new URLSearchParams();
      const scopes: string[] = Array.isArray(params.scopes)
        ? (params.scopes as string[])
        : typeof params.scopes === "string"
          ? [params.scopes]
          : [];
      for (const s of scopes) usp.append("scopes", s);
      return usp.toString();
    }
  });
  const url = resp.data?.authorization_url as string | undefined;
  if (!url) throw new Error("authorization_url not returned");
  try {
    const u = new URL(url);
    const redirectUri = u.searchParams.get("redirect_uri");
    if (!redirectUri) {
      u.searchParams.set("redirect_uri", window.location.origin + "/auth-callback.html");
    }
    window.location.href = u.toString();
  } catch {
    window.location.href = url;
  }
}
