// src/services/__tests__/desktopApi.notifications.test.js
import { notificationService } from '../desktopApi';
import { buildKey, readJSON, writeJSON, removeKey } from '../../utils/localStore';

const STORAGE_KEY = buildKey('notifications', 'list', false);

describe('notificationService — localStorage persistence', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.restoreAllMocks();
  });

  test('getAll renvoie les notifications par défaut quand le localStorage est vide', async () => {
    const { data } = await notificationService.getAll();
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBe(3);
    expect(data[0]).toHaveProperty('id');
    expect(data[0]).toHaveProperty('title');
  });

  test('getAll persiste les notifications par défaut dans le localStorage via getAll puis getAll', async () => {
    const { data } = await notificationService.getAll();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    await notificationService.save(data);
    const stored = readJSON(STORAGE_KEY, null);
    expect(stored).toEqual(data);
  });

  test('getAll renvoie les notifications stockées au lieu des défauts', async () => {
    const custom = [
      { id: 'x-1', title: 'Test', message: 'msg', time: 'now', read: false },
    ];
    writeJSON(STORAGE_KEY, custom);
    const { data } = await notificationService.getAll();
    expect(data).toEqual(custom);
  });

  test('readAll est synchrone et renvoie les notifications', () => {
    const list = notificationService.readAll();
    expect(Array.isArray(list)).toBe(true);
    expect(list.length).toBeGreaterThan(0);
  });

  test('add ajoute une notification et la persiste', async () => {
    const { data } = await notificationService.add({
      title: 'Nouvelle alerte',
      message: 'Stock faible',
    });
    expect(data.length).toBe(4);
    const stored = readJSON(STORAGE_KEY, null);
    expect(stored.length).toBe(4);
    expect(stored[0].title).toBe('Nouvelle alerte');
    expect(stored[0].read).toBe(false);
  });

  test('add ne duplique pas une notification existante', async () => {
    const { data: first } = await notificationService.add({ id: 'dup-1', title: 'Dup', message: 'm' });
    const { data: second } = await notificationService.add({ id: 'dup-1', title: 'Dup 2', message: 'm2' });
    expect(second.length).toBe(first.length);
    expect(second.find((n) => n.id === 'dup-1').title).toBe('Dup');
  });

  test('add génère un ID unique si non fourni', async () => {
    const { data } = await notificationService.add({ title: 'Auto ID', message: 'm' });
    const added = data.find((n) => n.title === 'Auto ID');
    expect(added).toBeDefined();
    expect(added.id).toBeTruthy();
    expect(typeof added.id).toBe('string');
  });

  test('markAsRead marque une notification comme lue', async () => {
    const { data: before } = await notificationService.getAll();
    const unreadId = before.find((n) => !n.read).id;

    const { data: after } = await notificationService.markAsRead(unreadId);
    const updated = after.find((n) => n.id === unreadId);
    expect(updated.read).toBe(true);

    const stored = readJSON(STORAGE_KEY, null);
    expect(stored.find((n) => n.id === unreadId).read).toBe(true);
  });

  test('markAllAsRead marque toutes les notifications comme lues', async () => {
    const { data: after } = await notificationService.markAllAsRead();
    expect(after.every((n) => n.read)).toBe(true);
    const stored = readJSON(STORAGE_KEY, null);
    expect(stored.every((n) => n.read)).toBe(true);
  });

  test('delete supprime une notification et la persiste', async () => {
    const { data: before } = await notificationService.getAll();
    const idToDelete = before[0].id;

    const { data: after } = await notificationService.delete(idToDelete);
    expect(after.length).toBe(before.length - 1);
    expect(after.find((n) => n.id === idToDelete)).toBeUndefined();

    const stored = readJSON(STORAGE_KEY, null);
    expect(stored.find((n) => n.id === idToDelete)).toBeUndefined();
  });

  test('save remplace la liste complète', async () => {
    const newList = [
      { id: 100, title: 'Replacé', message: 'm', time: 'now', read: true },
    ];
    await notificationService.save(newList);
    const { data } = await notificationService.getAll();
    expect(data).toEqual(newList);
  });

  test('clear vide la liste', async () => {
    await notificationService.clear();
    const { data } = await notificationService.getAll();
    expect(data).toEqual([]);
  });
});

describe('notificationService — Electron integration', () => {
  beforeEach(() => {
    localStorage.clear();
    (window.electron || (window.electron = {}));
  });

  afterEach(() => {
    delete window.electron;
  });

  test('triggerNative appelle window.electron.notify quand disponible', async () => {
    const mockNotify = jest.fn().mockResolvedValue(true);
    window.electron = { notify: mockNotify, setBadge: jest.fn().mockResolvedValue(true) };

    const result = await notificationService.triggerNative('Test', 'Body');
    expect(mockNotify).toHaveBeenCalledWith('Test', 'Body');
    expect(result).toBe(true);
  });

  test('triggerNative résout même sans Electron', async () => {
    delete window.electron;
    const result = await notificationService.triggerNative('Test', 'Body');
    expect(result).toBe(true);
  });

  test('setBadge appelle window.electron.setBadge quand disponible', async () => {
    const mockSetBadge = jest.fn().mockResolvedValue(true);
    window.electron = { notify: jest.fn(), setBadge: mockSetBadge };

    await notificationService.setBadge(5);
    expect(mockSetBadge).toHaveBeenCalledWith(5);
  });

  test('setBadge résout même sans Electron', async () => {
    delete window.electron;
    const result = await notificationService.setBadge(3);
    expect(result).toBe(true);
  });
});
