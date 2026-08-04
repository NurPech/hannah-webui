// Registers just enough to make the app installable (Add to Home Screen).
// No caching: the WebUI is a thin client over live gRPC data via Core, so
// there is nothing meaningful to show offline — an app-shell cache would
// only risk serving stale pages. Every request goes straight to the network.
self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
