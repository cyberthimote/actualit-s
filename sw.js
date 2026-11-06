const V='av-v1',SHELL=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(SHELL)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V).map(x=>caches.delete(x)))));self.clients.claim()});
self.addEventListener('fetch',e=>{
  const r=e.request,u=new URL(r.url);
  if(r.method!=='GET'||u.origin!==location.origin)return;
  const save=x=>{const c=x.clone();caches.open(V).then(h=>h.put(r,c));return x};
  e.respondWith(u.pathname.includes('/data/')
    ? fetch(r).then(save).catch(()=>caches.match(r))
    : caches.match(r).then(m=>{const n=fetch(r).then(save).catch(()=>m);return m||n}));
});
