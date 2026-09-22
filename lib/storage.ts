import type { Session } from "./types";
let connection: Promise<IDBDatabase>;
function db() {
  return (connection ??= new Promise((resolve, reject) => {
    const r = indexedDB.open("paopao-room-v1", 1);
    r.onupgradeneeded = () =>
      r.result.createObjectStore("sessions", { keyPath: "id" });
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  }));
}
export async function allSessions(): Promise<Session[]> {
  const d = await db();
  return new Promise((resolve, reject) => {
    const r = d.transaction("sessions").objectStore("sessions").getAll();
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}
export async function writeSession(session: Session) {
  const d = await db();
  return new Promise<void>((resolve, reject) => {
    const t = d.transaction("sessions", "readwrite");
    t.objectStore("sessions").put(session);
    t.oncomplete = () => resolve();
    t.onerror = () => reject(t.error);
  });
}
export async function deleteSession(id?: string) {
  const d = await db();
  return new Promise<void>((resolve, reject) => {
    const t = d.transaction("sessions", "readwrite");
    if (id) t.objectStore("sessions").delete(id);
    else t.objectStore("sessions").clear();
    t.oncomplete = () => resolve();
    t.onerror = () => reject(t.error);
  });
}
