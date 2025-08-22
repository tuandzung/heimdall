import axios from 'axios';

export async function startGoogleOAuth() {
  const resp = await axios.get('/auth/google/authorize', {
    params: { scopes: ['openid', 'email', 'profile'] },
    paramsSerializer: (params) => {
      const usp = new URLSearchParams();
      for (const s of params.scopes) usp.append('scopes', s);
      return usp.toString();
    },
  });
  const url = resp.data?.authorization_url;
  if (!url) throw new Error('authorization_url not returned');
  // Force redirect_uri to our static callback page if not already set server-side
  try {
    const u = new URL(url);
    const redirectUri = u.searchParams.get('redirect_uri');
    if (!redirectUri) {
      u.searchParams.set('redirect_uri', window.location.origin + '/auth-callback.html');
    }
    window.location.href = u.toString();
  } catch {
    window.location.href = url;
  }
}


