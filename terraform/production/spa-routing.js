function handler(event) {
  var request = event.request;
  var uri = request.uri;

  // /app/settings → /app/index.html  (SPA route, no extension)
  // /app/main.js  → unchanged        (static asset, has extension)
  if (uri.startsWith('/app') && !uri.includes('.')) {
    request.uri = '/app/index.html';
  }

  // /about/ → /about/index.html  (default_root_object only works for /)
  if (uri.endsWith('/')) {
    request.uri += 'index.html';
  }

  return request;
}
