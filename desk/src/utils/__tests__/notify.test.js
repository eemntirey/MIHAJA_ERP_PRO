// src/utils/__tests__/notify.test.js
import { notify, notifyError, notifyInfo, notifySuccess, notifyWarning, NOTIFICATION_EVENTS } from '../notify';
import { notificationService } from '../../services/desktopApi';

describe('notify utility', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('notify ajoute la notification au localStorage', async () => {
    await notify({ title: 'Test notify', message: 'Hello' });
    const list = notificationService.readAll();
    expect(list.find((n) => n.title === 'Test notify' && n.message === 'Hello')).toBeDefined();
  });

  test('notify déclenche une notification native Electron', async () => {
    const mockNotify = jest.fn().mockResolvedValue(true);
    const mockSetBadge = jest.fn().mockResolvedValue(true);
    (window.electron || (window.electron = {}));
    window.electron.notify = mockNotify;
    window.electron.setBadge = mockSetBadge;

    await notify({ title: 'Electron Test', message: 'Native' });
    expect(mockNotify).toHaveBeenCalledWith('Electron Test', 'Native');
    expect(mockSetBadge).toHaveBeenCalled();
  });

  test('notify met à jour le badge du dock', async () => {
    await notificationService.clear();

    const mockSetBadge = jest.fn().mockResolvedValue(true);
    (window.electron || (window.electron = {}));
    window.electron.setBadge = mockSetBadge;
    window.electron.notify = jest.fn().mockResolvedValue(true);

    // Ajoute 3 notifications non-lues
    await notify({ title: 'N1', message: 'm' });
    await notify({ title: 'N2', message: 'm' });
    await notify({ title: 'N3', message: 'm' });

    // Le dernier appel à setBadge devrait refléter 3 non-lues
    const lastCall = mockSetBadge.mock.calls[mockSetBadge.mock.calls.length - 1];
    expect(lastCall[0]).toBe(3);
  });

  test('notify déclenche un événement CustomEvent', async () => {
    const handler = jest.fn();
    window.addEventListener(NOTIFICATION_EVENTS.UPDATED, handler);

    await notify({ title: 'Event Test', message: 'm' });
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler.mock.calls[0][0].type).toBe('notifications:updated');
  });

  test('notifyError / notifyInfo / notifySuccess / notifyWarning utilisent les bons titres', async () => {
    await notifyError('Erreur critique');
    await notifyInfo('Info utile');
    await notifySuccess('Tout va bien');
    await notifyWarning('Attention');

    const list = notificationService.readAll();
    expect(list.find((n) => n.title === 'Erreur')).toBeDefined();
    expect(list.find((n) => n.title === 'Information')).toBeDefined();
    expect(list.find((n) => n.title === 'Succès')).toBeDefined();
    expect(list.find((n) => n.title === 'Attention')).toBeDefined();
  });
});
