// src/utils/notify.js
// Utilitaire autonome pour déclencher une notification depuis n'importe quel
// point de l'application (hors React hooks). Persiste en localStorage,
// déclenche la notification native Electron et met à jour le badge du dock.
import { notificationService } from '../services/desktopApi';

const NOTIFY_EVENT = 'notifications:updated';

export const NOTIFICATION_EVENTS = { UPDATED: NOTIFY_EVENT };

export const notify = async (notification) => {
  const result = await notificationService.add(notification).catch(() => null);

  const item = result?.data
    ? result.data.find((n) => n.id === (notification.id || result.data[0]?.id)) || result.data[0]
    : null;

  if (item) {
    await notificationService.triggerNative(item.title, item.message).catch(() => {});
  }

  const list = notificationService.readAll();
  const unread = list.filter((n) => !n.read).length;
  await notificationService.setBadge(unread).catch(() => {});

  window.dispatchEvent(new CustomEvent(NOTIFY_EVENT, { detail: { action: 'add' } }));
  return true;
};

export const notifyError = async (message) => notify({ title: 'Erreur', message, read: false });
export const notifyInfo = async (message) => notify({ title: 'Information', message, read: false });
export const notifySuccess = async (message) =>
  notify({ title: 'Succès', message, read: false });
export const notifyWarning = async (message) =>
  notify({ title: 'Attention', message, read: false });

export default notify;
